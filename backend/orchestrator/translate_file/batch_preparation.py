"""Batch planning helpers shared by the translation and review preparation tasks."""

import json
import re
from collections.abc import Callable
from typing import Any

from llm.interface import LLMInterface
from orchestrator.task_data.translation import TranslationBatch
from prompts.translate_file import generate_batch_plan_prompt, generate_split_batch_plan_prompt
from utils.logger import setup_logger

logger = setup_logger()


def build_lines_prompt(indexed_lines: list[str]) -> str:
    """Wrap indexed subtitle lines in an XML-style block for the LLM prompt."""
    transcript = "\n".join(indexed_lines)
    return f"""
        <SUBTITLE_LINES>
        {transcript}
        </SUBTITLE_LINES>
        """.strip()


def extract_json_payload(raw_output: str) -> str:
    """Extract the first JSON object from the LLM's raw output, stripping any markdown code fences."""
    cleaned = raw_output.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Batch planner did not return a JSON object.")
    return cleaned[start:end + 1].strip()


def parse_batches(
    raw_output: str,
    expected_start: int,
    expected_end: int,
    max_batch_size: int | None = None,
) -> list[TranslationBatch]:
    """Parse the LLM's JSON batch plan, checking contiguous coverage of the span and, if given, the size limit."""
    parsed = json.loads(extract_json_payload(raw_output))
    entries = parsed.get("batches")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Batch planner output must contain a non-empty 'batches' array.")

    batches: list[TranslationBatch] = []
    current_start = expected_start
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each batch entry must be a JSON object.")
        start_index = entry.get("start_index")
        end_index = entry.get("end_index")
        reason = entry.get("reason")
        if not isinstance(start_index, int) or not isinstance(end_index, int):
            raise ValueError("Each batch must contain integer start_index and end_index values.")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Each batch must contain a non-empty string reason.")
        if start_index > end_index:
            raise ValueError("Batch start_index cannot be greater than end_index.")
        if start_index != current_start:
            raise ValueError("Batch plan must cover subtitle lines contiguously without gaps or overlap.")
        if end_index > expected_end:
            raise ValueError("Batch plan references subtitle lines beyond the expected subtitle span.")
        if max_batch_size is not None and end_index - start_index + 1 > max_batch_size:
            raise ValueError(
                "Batch plan contains batches larger than the requested maximum batch size:\n"
                f"- {start_index}-{end_index} "
                f"(size {end_index - start_index + 1}, max {max_batch_size}): {reason.strip()}"
            )
        batches.append(TranslationBatch(start_index=start_index, end_index=end_index, reason=reason.strip()))
        current_start = end_index + 1

    if batches[0].start_index != expected_start:
        raise ValueError(f"Batch plan must start at subtitle line {expected_start}.")
    if batches[-1].end_index != expected_end:
        raise ValueError(f"Batch plan must end at subtitle line {expected_end}.")
    return batches


def plan_batches(
    llm: LLMInterface,
    indexed_lines: list[str],
    context: dict[str, str],
    input_lang: str,
    output_lang: str,
) -> list[TranslationBatch]:
    """Ask the LLM to group all subtitle lines into semantically coherent batches."""
    raw_output = llm.infer(
        prompt=build_lines_prompt(indexed_lines),
        system_prompt=generate_batch_plan_prompt(
            context=context if context else None,
            input_lang=input_lang,
            output_lang=output_lang,
        ),
        temperature=0.1,
    )
    return parse_batches(raw_output, expected_start=1, expected_end=len(indexed_lines))


def fallback_batches(batch: TranslationBatch, max_batch_size: int) -> list[TranslationBatch]:
    """Deterministically split a batch into equal-sized parts without calling the LLM."""
    parts: list[TranslationBatch] = []
    total_parts = (batch.size + max_batch_size - 1) // max_batch_size
    current_start = batch.start_index
    for part_index in range(total_parts):
        current_end = min(current_start + max_batch_size - 1, batch.end_index)
        parts.append(TranslationBatch(
            start_index=current_start,
            end_index=current_end,
            reason=f"{batch.reason} (deterministic split {part_index + 1}/{total_parts})".strip(),
        ))
        current_start = current_end + 1
    return parts


def split_oversized_batches(
    llm: LLMInterface,
    indexed_lines: list[str],
    batches: list[TranslationBatch],
    max_batch_size: int,
    context: dict[str, str],
    input_lang: str,
    output_lang: str,
    on_repaired: Callable[[int, int], None],
) -> tuple[list[TranslationBatch], list[dict[str, Any]]]:
    """Replace each batch larger than max_batch_size with LLM-split parts, falling back to an even split.

    Returns the repaired plan and one audit entry per repaired batch (original range, method, replacements).
    """
    oversized_count = sum(1 for batch in batches if batch.size > max_batch_size)
    repaired: list[TranslationBatch] = []
    repairs: list[dict[str, Any]] = []
    for batch in batches:
        if batch.size <= max_batch_size:
            repaired.append(batch)
            continue

        raw_output = ""
        repair: dict[str, Any] = {"original": batch.to_log(), "max_batch_size": max_batch_size}
        try:
            raw_output = llm.infer(
                prompt=build_lines_prompt(indexed_lines[batch.start_index - 1:batch.end_index]),
                system_prompt=generate_split_batch_plan_prompt(
                    context=context if context else None,
                    input_lang=input_lang,
                    output_lang=output_lang,
                    max_batch_size=max_batch_size,
                    original_reason=batch.reason,
                ),
                temperature=0.1,
            )
            parts = parse_batches(raw_output, batch.start_index, batch.end_index, max_batch_size)
            repair["method"] = "model"
        except Exception as exc:
            parts = fallback_batches(batch, max_batch_size)
            repair["method"] = "deterministic_fallback"
            repair["failure"] = str(exc)
            repair["raw_output"] = raw_output
            logger.warning(
                "Oversized batch fallback: original=%s-%s deterministic_split=%s max_batch_size=%s failure=%s",
                batch.start_index, batch.end_index,
                ",".join(f"{part.start_index}-{part.end_index}" for part in parts), max_batch_size, exc,
            )
        repair["replacements"] = [part.to_log() for part in parts]
        repairs.append(repair)
        repaired.extend(parts)
        on_repaired(len(repairs), oversized_count)
    return repaired, repairs


def validate_final_batches(batches: list[TranslationBatch], total_lines: int, max_batch_size: int) -> None:
    """Raise ValueError if the plan is not contiguous over all lines or still has an oversized batch."""
    if not batches:
        raise ValueError("Batch planner output must contain a non-empty 'batches' array.")
    contiguous_start = 1
    oversized_lines: list[str] = []
    for batch in batches:
        if batch.start_index != contiguous_start:
            raise ValueError("Batch plan must cover subtitle lines contiguously without gaps or overlap.")
        if batch.end_index < batch.start_index:
            raise ValueError("Batch start_index cannot be greater than end_index.")
        if batch.size > max_batch_size:
            oversized_lines.append(f"- {batch.start_index}-{batch.end_index} (size {batch.size}, max {max_batch_size}): {batch.reason}")
        contiguous_start = batch.end_index + 1
    if batches[-1].end_index != total_lines:
        raise ValueError(f"Batch plan must end at subtitle line {total_lines}.")
    if oversized_lines:
        raise ValueError("Batch plan contains batches larger than the requested maximum batch size:\n" + "\n".join(oversized_lines))

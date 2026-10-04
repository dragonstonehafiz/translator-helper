import json
from dataclasses import replace
from typing import Any

from llm.interface import LLMInterface
from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.library_update import CharacterUpdateProposal, LibraryProposals, ProposedLibraryData
from prompts.library import deduplicate_proposals_prompt
from utils.logger import setup_logger

logger = setup_logger("translator-helper")


class TaskDeduplicateCharacterUpdates(BaseTask[ProposedLibraryData, ProposedLibraryData]):
    """Library update stage 6: drop proposed character facts the library already records; other categories pass through."""

    input_type = ProposedLibraryData
    output_type = ProposedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> ProposedLibraryData:
        """Group personality/history/relationship additions and ask the LLM, per group, which ones are new."""
        data = self.get_data()
        proposals = data.proposals
        updated = proposals["updated_characters"]
        if not updated:
            self._write_log(write_log, proposals, proposals, {})
            return data

        # personality / history -> { char_id: [updates] }; relationships -> { other character name: [updates] }
        personality_groups: dict[str, list[CharacterUpdateProposal]] = {}
        history_groups: dict[str, list[CharacterUpdateProposal]] = {}
        relationship_groups: dict[str, list[CharacterUpdateProposal]] = {}
        for u in updated:
            if u["field"] == "personality":
                personality_groups.setdefault(u["id"], []).append(u)
            elif u["field"] == "history":
                history_groups.setdefault(u["id"], []).append(u)
            elif u["field"] == "relationships":
                relationship_groups.setdefault(u.get("character", ""), []).append(u)

        characters = data.series["characters"]
        char_map = {c["id"]: c for c in characters}
        kept: list[CharacterUpdateProposal] = []
        existing_by_group: dict[str, list[str]] = {}
        total_calls = len(personality_groups) + len(history_groups) + len(relationship_groups)
        completed = 0

        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()
        try:
            report_progress(0, total_calls, "Deduplicating proposals", 0.0)
            for field_name, groups in (("personality", personality_groups), ("history", history_groups)):
                for char_id, proposals_list in groups.items():
                    char = char_map.get(char_id)
                    existing = char[field_name] if char else []
                    existing_by_group[f"{char_id} | {field_name}"] = existing
                    kept_indices = self._dedup_call(llm, field_name, existing, proposals_list)
                    kept.extend(proposals_list[i] for i in kept_indices)
                    completed += 1
                    name = char["name"] if char else char_id
                    report_progress(completed, total_calls, f"Checked {field_name} for {name}", 0.0)

            for rel_char, proposals_list in relationship_groups.items():
                existing = [fact for c in characters for fact in c["relationships"].get(rel_char, [])]
                existing_by_group[f"relationships | {rel_char}"] = existing
                kept_indices = self._dedup_call(llm, f"relationships[{rel_char}]", existing, proposals_list)
                kept.extend(proposals_list[i] for i in kept_indices)
                completed += 1
                report_progress(completed, total_calls, f"Checked relationship: {rel_char}", 0.0)
        finally:
            model_manager.release_llm()

        deduped: LibraryProposals = {**proposals, "updated_characters": kept}
        report_progress(total_calls, total_calls, f"Kept {len(kept)}/{len(updated)} updated_characters proposals", 0.0)
        self._write_log(write_log, proposals, deduped, existing_by_group)
        return replace(data, proposals=deduped)

    def _write_log(
        self,
        write_log: WriteLog,
        original: LibraryProposals,
        deduped: LibraryProposals,
        existing_by_group: dict[str, list[str]],
    ) -> None:
        """Write a per-group audit of existing library data, proposed additions, and kept and excluded entries."""
        deduped_set = {(u["id"], u["field"], u.get("character", ""), u["append"]) for u in deduped["updated_characters"]}
        groups: dict[str, dict[str, Any]] = {}
        for u in original["updated_characters"]:
            key = f"{u['id']} | {u['field']}" + (f" | {u['character']}" if "character" in u else "")
            if key not in groups:
                existing_key = f"{u['id']} | {u['field']}" if "character" not in u else f"relationships | {u['character']}"
                groups[key] = {
                    "existing_in_library": existing_by_group.get(existing_key, []),
                    "proposed": [],
                    "kept": [],
                    "excluded": [],
                }
            bucket = "kept" if (u["id"], u["field"], u.get("character", ""), u["append"]) in deduped_set else "excluded"
            groups[key]["proposed"].append(u["append"])
            groups[key][bucket].append(u["append"])

        write_log("06-deduplicate-proposals.json", {
            "updated_characters_dedup": groups,
            "new_characters": deduped["new_characters"],
            "new_glossary": deduped["new_glossary"],
        })

    def _dedup_call(self, llm: LLMInterface, field: str, existing: list[str], proposals_list: list[CharacterUpdateProposal]) -> list[int]:
        """Ask the LLM which proposed entries are new and return their 0-based indices; keeps all if the call fails."""
        existing_text = "\n".join(f"- {e}" for e in existing) if existing else "(none)"
        proposed_lines = "\n".join(f"{i + 1}. {p['append']}" for i, p in enumerate(proposals_list))
        prompt = f"=== EXISTING {field.upper()} ENTRIES ===\n{existing_text}\n\n=== PROPOSED ADDITIONS ===\n{proposed_lines}"
        try:
            raw = llm.infer(prompt=prompt, system_prompt=deduplicate_proposals_prompt(field), temperature=0.0)
            text = raw.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                indices = json.loads(text[start:end])
                return [i - 1 for i in indices if isinstance(i, int) and 1 <= i <= len(proposals_list)]
            return list(range(len(proposals_list)))
        except Exception as exc:
            logger.warning("Dedup call failed for field %s: %s — keeping all proposals", field, exc)
            return list(range(len(proposals_list)))

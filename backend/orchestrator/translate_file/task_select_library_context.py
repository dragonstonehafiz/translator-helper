import json
from dataclasses import replace
from typing import TypeVar

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.library_types import CharacterEntry, GlossaryEntry, LibraryContext
from orchestrator.task_data.translation import TranslationData
from prompts.library_context import select_library_context_prompt
from utils.subtitles import numbered_lines

PlannedT = TypeVar("PlannedT", bound=TranslationData)


class TaskSelectLibraryContext(BaseTask[PlannedT, PlannedT]):
    """Shared translation/review stage: pick the series characters and glossary terms relevant to this file.

    Construct it with the concrete data class it runs on; it returns that same class unchanged except for
    `context` and `library_context`.
    """

    def __init__(self, data_type: type[PlannedT]):
        """Run on (and return) `data_type`, e.g. PlannedTranslationData or PlannedReviewData."""
        super().__init__()
        self.input_type = data_type
        self.output_type = data_type

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> PlannedT:
        """Ask the LLM which library entries appear in the file and add them to the prompt context."""
        data = self.get_data()
        series = data.series
        characters = series["characters"] if series else []
        glossary = series["glossary"] if series else []
        series_name = series["name"] if series else ""

        if not series_name or (not characters and not glossary):
            report_progress(1, 1, "No library data — skipping context selection", 0.0)
            return data

        report_progress(0, 1, "Selecting relevant library entries for this episode", 0.0)
        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()
        try:
            raw = llm.infer(
                prompt="\n".join(numbered_lines(data.subtitles)),
                system_prompt=select_library_context_prompt(
                    series_name=series_name,
                    input_lang=data.input_lang,
                    output_lang=data.output_lang,
                    character_ids=[c["id"] for c in characters],
                    character_names=[c["name"] for c in characters],
                    glossary_ids=[t["id"] for t in glossary],
                    glossary_terms=[t["term"] for t in glossary],
                ),
                temperature=0.1,
            )
        finally:
            model_manager.release_llm()

        selected_char_ids, selected_glossary_ids = self._parse_selection(raw)
        char_lookup = {c["id"]: c for c in characters}
        term_lookup = {t["id"]: t for t in glossary}
        selected_characters = [char_lookup[cid] for cid in selected_char_ids if cid in char_lookup]
        selected_glossary = [term_lookup[tid] for tid in selected_glossary_ids if tid in term_lookup]

        context = dict(data.context)
        if selected_characters:
            context["characters"] = self._format_characters(selected_characters)
        if selected_glossary:
            context["glossary"] = self._format_glossary(selected_glossary)
        library_context: LibraryContext = {
            "selected_characters": selected_characters,
            "selected_glossary": selected_glossary,
        }

        report_progress(1, 1, f"Selected {len(selected_characters)} characters and {len(selected_glossary)} glossary terms", 0.0)
        return replace(data, context=context, library_context=library_context)

    def _parse_selection(self, raw: str) -> tuple[list[str], list[str]]:
        """Parse the LLM JSON response into character and glossary ID lists."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        parsed = json.loads(text)
        char_ids = [str(cid) for cid in parsed.get("character_ids", [])]
        glossary_ids = [str(tid) for tid in parsed.get("glossary_ids", [])]
        return char_ids, glossary_ids

    def _format_characters(self, characters: list[CharacterEntry]) -> str:
        """Format selected character entries as a readable text block."""
        blocks = []
        for char in characters:
            lines = [f"{char['name']}"]
            aliases = char.get("aliases") or []
            if aliases:
                lines.append(f"  Aliases: {', '.join(aliases)}")
            personality = char.get("personality") or []
            if personality:
                lines.append(f"  Personality: {'; '.join(personality)}")
            history = char.get("history") or []
            if history:
                lines.append(f"  History: {'; '.join(history)}")
            relationships = char.get("relationships") or {}
            for other, descs in relationships.items():
                if descs:
                    lines.append(f"  Relationship with {other}: {'; '.join(descs)}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _format_glossary(self, glossary: list[GlossaryEntry]) -> str:
        """Format selected glossary entries as a readable text block."""
        lines = []
        for term in glossary:
            entry = f"{term['term']} → {term['translation']}"
            notes = term.get("notes", "").strip()
            if notes:
                entry += f" ({notes})"
            lines.append(entry)
        return "\n".join(lines)

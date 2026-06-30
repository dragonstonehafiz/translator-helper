import json
from pathlib import Path

import pysubs2

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library_context import select_library_context_prompt


class TaskSelectLibraryContext(BaseTask):
    """Select relevant characters and glossary terms from the series library for this subtitle file."""

    TASK_TYPE = "TaskSelectLibraryContext"
    LOG_FILENAME = "03-select-library-context.json"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Read the subtitle file and series library, ask the LLM to select relevant entries, merge into context."""
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        series = data.get("series") or {}
        context = dict(data.get("context") or {})
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))
        log_dir = str(data.get("log_dir", ""))

        result_handler.set_processing(self.task_type)

        characters = series.get("characters") or []
        glossary = series.get("glossary") or []
        series_name = series.get("name", "")

        # No series or empty library — pass through without an LLM call.
        if not series_name or (not characters and not glossary):
            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": "No library data — skipping context selection", "eta_seconds": 0})
            result_handler.set_complete(self.task_type)
            return {**data}

        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        progress_handler.set(self.task_type, {"current": 0, "total": 1, "status": "Selecting relevant library entries for this episode", "eta_seconds": 0})

        try:
            llm_client.set_running(True)
            transcript = self._load_transcript(file_path)
            character_ids = [c["id"] for c in characters]
            character_names = [c["name"] for c in characters]
            glossary_ids = [t["id"] for t in glossary]
            glossary_terms = [t["term"] for t in glossary]

            raw = model_manager.llm_infer(
                prompt=transcript,
                system_prompt=select_library_context_prompt(
                    series_name=series_name,
                    input_lang=input_lang,
                    output_lang=output_lang,
                    character_ids=character_ids,
                    character_names=character_names,
                    glossary_ids=glossary_ids,
                    glossary_terms=glossary_terms,
                ),
                temperature=0.1,
            )

            selected_char_ids, selected_glossary_ids = self._parse_selection(raw)

            char_lookup = {c["id"]: c for c in characters}
            term_lookup = {t["id"]: t for t in glossary}
            selected_characters = [char_lookup[cid] for cid in selected_char_ids if cid in char_lookup]
            selected_glossary = [term_lookup[tid] for tid in selected_glossary_ids if tid in term_lookup]

            if selected_characters:
                context["characters"] = self._format_characters(selected_characters)
            if selected_glossary:
                context["glossary"] = self._format_glossary(selected_glossary)

            library_context = {
                "selected_characters": selected_characters,
                "selected_glossary": selected_glossary,
            }

            if log_dir:
                self._write_log(log_dir, raw, series_name, len(characters), len(glossary), library_context)

            progress_handler.set(
                self.task_type,
                {
                    "current": 1,
                    "total": 1,
                    "status": f"Selected {len(selected_characters)} characters and {len(selected_glossary)} glossary terms",
                    "eta_seconds": 0,
                },
            )
            result_handler.set_complete(self.task_type)
            return {**data, "context": context, "library_context": library_context}

        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _load_transcript(self, file_path: str) -> str:
        """Load subtitle lines as a numbered transcript string."""
        subs = pysubs2.load(file_path)
        lines = []
        for index, line in enumerate(subs, start=1):
            speaker = line.name.strip() if line.name else "Unknown"
            text = line.text.strip() or "[EMPTY]"
            lines.append(f"{index}. {speaker}: {text}")
        return "\n".join(lines)

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

    def _format_characters(self, characters: list[dict]) -> str:
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

    def _format_glossary(self, glossary: list[dict]) -> str:
        """Format selected glossary entries as a readable text block."""
        lines = []
        for term in glossary:
            entry = f"{term['term']} → {term['translation']}"
            notes = term.get("notes", "").strip()
            if notes:
                entry += f" ({notes})"
            lines.append(entry)
        return "\n".join(lines)

    def _write_log(
        self,
        log_dir: str,
        raw: str,
        series_name: str,
        total_characters: int,
        total_glossary: int,
        library_context: dict,
    ) -> None:
        """Write the selection log to the per-run log directory."""
        output_dir = Path(log_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_payload = {
            "task_type": self.task_type,
            "series_name": series_name,
            "total_characters": total_characters,
            "total_glossary": total_glossary,
            "selected_character_count": len(library_context["selected_characters"]),
            "selected_glossary_count": len(library_context["selected_glossary"]),
            "selected_characters": library_context["selected_characters"],
            "selected_glossary": library_context["selected_glossary"],
            "raw_output": raw,
        }
        with open(output_dir / self.LOG_FILENAME, "w", encoding="utf-8") as f:
            json.dump(log_payload, f, ensure_ascii=False, indent=2)

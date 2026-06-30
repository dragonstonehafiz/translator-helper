import json
import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library import generate_library_proposals_prompt
from utils.utils import load_sub_data


class TaskGenerateLibraryProposals(BaseTask):
    """Library update chain task (slot 05): generate structured proposals for new/updated characters and glossary terms."""

    TASK_TYPE = "TaskGenerateLibraryProposals"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Build the LLM prompt from subtitle, library, and search results, then parse and return structured proposals."""
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        series = data.get("series", {})
        series_name = series.get("name", "Unknown Series")
        input_lang = series.get("input_lang", "ja")
        output_lang = series.get("output_lang", "en")
        search_results = data.get("search_results", [])
        known = data.get("known", {})
        log_dir = data.get("log_dir", "")

        result_handler.set_processing(self.task_type)
        progress_handler.set(self.task_type, {"current": 0, "total": 1, "status": "Generating library update proposals", "eta_seconds": 0})

        try:
            llm_client.set_running(True)
            transcript = "\n".join(load_sub_data(file_path, include_speaker=True))

            prompt_parts = [
                f"=== SUBTITLE FILE ===\n{transcript}",
                f"\n=== EXISTING LIBRARY ===\n{json.dumps({'characters': series.get('characters', []), 'glossary': series.get('glossary', [])}, ensure_ascii=False, indent=2)}",
                f"\n=== ALREADY KNOWN (do not re-add) ===\n{json.dumps(known, ensure_ascii=False)}",
            ]
            if search_results:
                prompt_parts.append(f"\n=== WEB SEARCH RESULTS ===\n{json.dumps(search_results, ensure_ascii=False, indent=2)}")

            prompt = "\n".join(prompt_parts)

            raw = model_manager.llm_infer(
                prompt=prompt,
                system_prompt=generate_library_proposals_prompt(series_name, input_lang, output_lang),
                temperature=0.2,
            )
            proposals = self._parse_proposals(raw)

            if log_dir:
                self._write_log(log_dir, raw, proposals)

            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": "Proposals generated", "eta_seconds": 0})
            result_handler.set_complete(self.task_type, {"proposals": proposals})
            return {**data, "proposals": proposals}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _parse_proposals(self, raw: str) -> dict:
        """Parse the LLM's proposals JSON and filter updated_characters to only valid field names; raises ValueError on malformed output."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            valid_character_update_fields = {"personality", "relationships", "history"}
            updated_characters = [
                u for u in parsed.get("updated_characters", [])
                if u.get("field") in valid_character_update_fields
            ]
            return {
                "new_characters": parsed.get("new_characters", []),
                "updated_characters": updated_characters,
                "new_glossary": parsed.get("new_glossary", []),
                "updated_glossary": parsed.get("updated_glossary", []),
            }
        except Exception as exc:
            raise ValueError(f"TaskGenerateLibraryProposals: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

    def _write_log(self, log_dir: str, raw: str, proposals: dict) -> None:
        """Write raw output and parsed proposals to 05-generate-library-proposals.json in the run's log directory."""
        path = os.path.join(log_dir, "05-generate-library-proposals.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"raw_output": raw, "proposals": proposals}, f, ensure_ascii=False, indent=2)

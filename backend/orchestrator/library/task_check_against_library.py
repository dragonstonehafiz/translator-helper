import json
import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library import check_against_library_prompt


class TaskCheckAgainstLibrary(BaseTask):
    """Library update chain task (slot 02): classify scan findings as known (already in library) or unknown (needs research)."""

    TASK_TYPE = "TaskCheckAgainstLibrary"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Ask the LLM to classify findings against the existing library and pass known/unknown sets forward."""
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        data = self.get_data()
        series = data.get("series", {})
        series_name = series.get("name", "Unknown Series")
        findings = data.get("findings", {"characters": [], "terms": [], "events": []})
        known_names = data.get("known_names", [])
        known_terms = data.get("known_terms", [])
        log_dir = data.get("log_dir", "")

        result_handler.set_processing(self.task_type)
        progress_handler.set(self.task_type, {"current": 0, "total": 1, "status": "Classifying findings against library", "eta_seconds": 0})

        try:
            llm_client.set_running(True)
            prompt = json.dumps(findings, ensure_ascii=False)
            raw = model_manager.llm_infer(
                prompt=prompt,
                system_prompt=check_against_library_prompt(series_name, known_names, known_terms),
                temperature=0.0,
            )
            result = self._parse_result(raw)
            known = result["known"]
            unknown = result["unknown"]

            if log_dir:
                self._write_log(log_dir, raw, findings, known, unknown)

            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": f"{len(unknown['characters'])} unknown characters, {len(unknown['terms'])} unknown terms", "eta_seconds": 0})
            result_handler.set_complete(self.task_type)
            return {**data, "known": known, "unknown": unknown}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _parse_result(self, raw: str) -> dict:
        """Parse the LLM's {known, unknown} classification JSON; raises ValueError on malformed output."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            known = parsed.get("known", {})
            unknown = parsed.get("unknown", {})
            return {
                "known": {
                    "characters": [str(c) for c in known.get("characters", [])],
                    "terms": [str(t) for t in known.get("terms", [])],
                },
                "unknown": {
                    "characters": [str(c) for c in unknown.get("characters", [])],
                    "terms": [str(t) for t in unknown.get("terms", [])],
                    "events": [str(e) for e in unknown.get("events", [])],
                },
            }
        except Exception as exc:
            raise ValueError(f"TaskCheckAgainstLibrary: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

    def _write_log(self, log_dir: str, raw: str, findings: dict, known: dict, unknown: dict) -> None:
        """Write raw output and classification results to 02-check-against-library.json in the run's log directory."""
        path = os.path.join(log_dir, "02-check-against-library.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"raw_output": raw, "findings": findings, "known": known, "unknown": unknown}, f, ensure_ascii=False, indent=2)

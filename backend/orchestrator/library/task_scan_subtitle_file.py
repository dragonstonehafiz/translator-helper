import json
import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library import scan_subtitle_file_prompt
from utils.utils import load_sub_data


class TaskScanSubtitleFile(BaseTask):
    TASK_TYPE = "TaskScanSubtitleFile"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
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
        known_names = data.get("known_names", [])
        known_terms = data.get("known_terms", [])
        log_dir = data.get("log_dir", "")

        result_handler.set_processing(self.task_type)
        progress_handler.set(self.task_type, {"current": 0, "total": 1, "status": "Scanning subtitle file for characters and terms", "eta_seconds": 0})

        try:
            llm_client.set_running(True)
            transcript = "\n".join(load_sub_data(file_path, include_speaker=True))
            raw = model_manager.llm_infer(
                prompt=transcript,
                system_prompt=scan_subtitle_file_prompt(series_name, input_lang, output_lang, known_names, known_terms),
                temperature=0.1,
            )
            findings = self._parse_findings(raw)

            if log_dir:
                self._write_log(log_dir, raw, findings)

            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": f"Found {len(findings['characters'])} characters, {len(findings['terms'])} terms", "eta_seconds": 0})
            result_handler.set_complete(self.task_type)
            return {**data, "findings": findings}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _parse_findings(self, raw: str) -> dict:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            return {
                "characters": [str(c) for c in parsed.get("characters", [])],
                "terms": [str(t) for t in parsed.get("terms", [])],
                "events": [str(e) for e in parsed.get("events", [])],
            }
        except Exception as exc:
            raise ValueError(f"TaskScanSubtitleFile: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

    def _write_log(self, log_dir: str, raw: str, findings: dict) -> None:
        path = os.path.join(log_dir, "01-scan-subtitle-file.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"raw_output": raw, "findings": findings}, f, ensure_ascii=False, indent=2)

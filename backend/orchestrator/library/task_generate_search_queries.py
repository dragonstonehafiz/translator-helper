import json
import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library import generate_search_queries_prompt


class TaskGenerateSearchQueries(BaseTask):
    TASK_TYPE = "TaskGenerateSearchQueries"

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
        series = data.get("series", {})
        series_name = series.get("name", "Unknown Series")
        unknown = data.get("unknown", {"characters": [], "terms": [], "events": []})
        log_dir = data.get("log_dir", "")

        all_unknowns = unknown.get("characters", []) + unknown.get("terms", [])

        result_handler.set_processing(self.task_type)
        progress_handler.set(self.task_type, {"current": 0, "total": 1, "status": f"Generating search queries for {len(all_unknowns)} unknown items", "eta_seconds": 0})

        try:
            if not all_unknowns:
                progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": "No unknown items — skipping search query generation", "eta_seconds": 0})
                result_handler.set_complete(self.task_type)
                if log_dir:
                    self._write_log(log_dir, "", [])
                return {**data, "search_queries": []}

            llm_client.set_running(True)
            prompt = f"Unknown items to search for:\n{json.dumps(all_unknowns, ensure_ascii=False)}"
            raw = model_manager.llm_infer(
                prompt=prompt,
                system_prompt=generate_search_queries_prompt(series_name),
                temperature=0.1,
            )
            queries = self._parse_queries(raw)

            if log_dir:
                self._write_log(log_dir, raw, queries)

            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": f"Generated {len(queries)} search queries", "eta_seconds": 0})
            result_handler.set_complete(self.task_type)
            return {**data, "search_queries": queries}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

    def _parse_queries(self, raw: str) -> list[dict]:
        text = raw.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            return [q for q in parsed if isinstance(q, dict) and "subject" in q and "query" in q]
        except Exception as exc:
            raise ValueError(f"TaskGenerateSearchQueries: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

    def _write_log(self, log_dir: str, raw: str, queries: list) -> None:
        path = os.path.join(log_dir, "03-generate-search-queries.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"raw_output": raw, "search_queries": queries}, f, ensure_ascii=False, indent=2)

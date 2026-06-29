import json
import os

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger

logger = setup_logger("translator-helper")


class TaskWebSearch(BaseTask):
    TASK_TYPE = "TaskWebSearch"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()

        data = self.get_data()
        queries = data.get("search_queries", [])
        log_dir = data.get("log_dir", "")

        result_handler.set_processing(self.task_type)

        if not queries:
            progress_handler.set(self.task_type, {"current": 1, "total": 1, "status": "No search queries — skipping web search", "eta_seconds": 0})
            result_handler.set_complete(self.task_type)
            if log_dir:
                self._write_log(log_dir, [])
            return {**data, "search_results": []}

        search_client = model_manager.get_search_client()
        if search_client is None:
            msg = "Tavily search not loaded. Please load the search model in Settings first."
            result_handler.set_error(self.task_type, msg)
            raise RuntimeError(msg)
        if not model_manager.is_search_ready():
            status = search_client.get_status()
            load_error = model_manager.search_loading_error or "unknown error"
            msg = f"Tavily search is in '{status}' state. Load error: {load_error}. Please reload the search model in Settings."
            result_handler.set_error(self.task_type, msg)
            raise RuntimeError(msg)

        progress_handler.set(self.task_type, {"current": 0, "total": len(queries), "status": "Running web searches", "eta_seconds": 0})

        try:
            search_results = []
            for i, q in enumerate(queries):
                subject = q.get("subject", "")
                query = q.get("query", "")
                try:
                    snippets = search_client.search(query, max_results=5)
                    search_results.append({"subject": subject, "results": snippets})
                    logger.info("Web search completed: subject=%s query=%s results=%d", subject, query, len(snippets))
                except Exception as exc:
                    logger.error("Web search failed: subject=%s error=%s", subject, exc)
                    result_handler.set_error(self.task_type, f"Web search failed for '{subject}': {exc}")
                    raise
                progress_handler.set(self.task_type, {"current": i + 1, "total": len(queries), "status": f"Searched {i + 1}/{len(queries)}", "eta_seconds": 0})

            if log_dir:
                self._write_log(log_dir, search_results)

            result_handler.set_complete(self.task_type)
            return {**data, "search_results": search_results}
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise

    def _write_log(self, log_dir: str, search_results: list) -> None:
        path = os.path.join(log_dir, "04-web-search.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"search_results": search_results}, f, ensure_ascii=False, indent=2)

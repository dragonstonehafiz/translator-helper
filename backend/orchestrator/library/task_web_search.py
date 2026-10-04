from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.library_update import QueriedLibraryData, SearchResult, SearchedLibraryData
from utils.logger import setup_logger

logger = setup_logger("translator-helper")


class TaskWebSearch(BaseTask[QueriedLibraryData, SearchedLibraryData]):
    """Library update stage 4: run each search query through Tavily and collect result snippets."""

    input_type = QueriedLibraryData
    output_type = SearchedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> SearchedLibraryData:
        """Run every query; with no queries, return empty results without needing a search client."""
        data = self.get_data()
        queries = data.search_queries
        if not queries:
            report_progress(1, 1, "No search queries — skipping web search", 0.0)
            write_log("04-web-search.json", {"search_results": []})
            return extend(data, SearchedLibraryData, search_results=[])

        model_manager = ModelManager.get_instance()
        search_client = model_manager.get_search_client()
        if search_client is None:
            raise RuntimeError("Tavily search not loaded. Please load the search model in Settings first.")
        if not model_manager.is_search_ready():
            load_error = model_manager.search_loading_error or "unknown error"
            raise RuntimeError(
                f"Tavily search is in '{search_client.state.value}' state. Load error: {load_error}. "
                "Please reload the search model in Settings."
            )

        report_progress(0, len(queries), "Running web searches", 0.0)
        search_results: list[SearchResult] = []
        for i, query in enumerate(queries):
            try:
                snippets = search_client.search(query["query"], max_results=5)
            except Exception as exc:
                logger.error("Web search failed: subject=%s error=%s", query["subject"], exc)
                raise RuntimeError(f"Web search failed for '{query['subject']}': {exc}") from exc
            search_results.append({"subject": query["subject"], "results": snippets})
            logger.info("Web search completed: subject=%s query=%s results=%d", query["subject"], query["query"], len(snippets))
            report_progress(i + 1, len(queries), f"Searched {i + 1}/{len(queries)}", 0.0)

        write_log("04-web-search.json", {"search_results": search_results})
        return extend(data, SearchedLibraryData, search_results=search_results)

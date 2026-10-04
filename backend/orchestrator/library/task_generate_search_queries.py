import json

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.library_update import ClassifiedLibraryData, QueriedLibraryData, SearchQuery
from prompts.library import generate_search_queries_prompt


class TaskGenerateSearchQueries(BaseTask[ClassifiedLibraryData, QueriedLibraryData]):
    """Library update stage 3: write a web search query for each unknown character or term (events are not searched)."""

    input_type = ClassifiedLibraryData
    output_type = QueriedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> QueriedLibraryData:
        """Ask the LLM for queries; with no unknown names or terms, return an empty list without calling it."""
        data = self.get_data()
        all_unknowns = data.unknown.characters + data.unknown.terms
        if not all_unknowns:
            report_progress(1, 1, "No unknown items — skipping search query generation", 0.0)
            write_log("03-generate-search-queries.json", {"raw_output": "", "search_queries": []})
            return extend(data, QueriedLibraryData, search_queries=[])

        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()
        try:
            report_progress(0, 1, f"Generating search queries for {len(all_unknowns)} unknown items", 0.0)
            raw = llm.infer(
                prompt=f"Unknown items to search for:\n{json.dumps(all_unknowns, ensure_ascii=False)}",
                system_prompt=generate_search_queries_prompt(data.series["name"]),
                temperature=0.1,
            )
        finally:
            model_manager.release_llm()

        queries = self._parse_queries(raw)
        write_log("03-generate-search-queries.json", {"raw_output": raw, "search_queries": queries})
        report_progress(1, 1, f"Generated {len(queries)} search queries", 0.0)
        return extend(data, QueriedLibraryData, search_queries=queries)

    def _parse_queries(self, raw: str) -> list[SearchQuery]:
        """Parse the LLM's JSON array of {subject, query} objects; raises ValueError on malformed output."""
        text = raw.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            return [
                {"subject": str(q["subject"]), "query": str(q["query"])}
                for q in parsed
                if isinstance(q, dict) and "subject" in q and "query" in q
            ]
        except Exception as exc:
            raise ValueError(f"{self.task_type}: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

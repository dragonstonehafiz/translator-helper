import json

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.library_update import ClassifiedLibraryData, ExtractedLibraryData, Findings
from prompts.library import check_against_library_prompt


class TaskClassifyLibraryFindings(BaseTask[ExtractedLibraryData, ClassifiedLibraryData]):
    """Library update stage 2: split findings into those already in the library (known) and those to research."""

    input_type = ExtractedLibraryData
    output_type = ClassifiedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> ClassifiedLibraryData:
        """Ask the LLM to classify the findings against the series' known names and terms."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()
        try:
            report_progress(0, 1, "Classifying findings against library", 0.0)
            raw = llm.infer(
                prompt=json.dumps(data.findings.to_log(), ensure_ascii=False),
                system_prompt=check_against_library_prompt(data.series["name"], data.known_names, data.known_terms),
                temperature=0.0,
            )
        finally:
            model_manager.release_llm()

        known, unknown = self._parse_result(raw)
        write_log("02-check-against-library.json", {
            "raw_output": raw,
            "findings": data.findings.to_log(),
            "known": known.to_log(),
            "unknown": unknown.to_log(),
        })
        report_progress(1, 1, f"{len(unknown.characters)} unknown characters, {len(unknown.terms)} unknown terms", 0.0)
        return extend(data, ClassifiedLibraryData, known=known, unknown=unknown)

    def _parse_result(self, raw: str) -> tuple[Findings, Findings]:
        """Parse the {known, unknown} classification; events stay with unknown, so known.events is always empty."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            known = parsed.get("known", {})
            unknown = parsed.get("unknown", {})
            return (
                Findings(
                    characters=[str(c) for c in known.get("characters", [])],
                    terms=[str(t) for t in known.get("terms", [])],
                    events=[],
                ),
                Findings(
                    characters=[str(c) for c in unknown.get("characters", [])],
                    terms=[str(t) for t in unknown.get("terms", [])],
                    events=[str(e) for e in unknown.get("events", [])],
                ),
            )
        except Exception as exc:
            raise ValueError(f"{self.task_type}: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

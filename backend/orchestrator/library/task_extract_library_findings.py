import json

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.library_update import ExtractedLibraryData, Findings, LibraryUpdateData
from prompts.library import scan_subtitle_file_prompt


class TaskExtractLibraryFindings(BaseTask[LibraryUpdateData, ExtractedLibraryData]):
    """Library update stage 1: find the character names, terms and events mentioned in the subtitle file."""

    input_type = LibraryUpdateData
    output_type = ExtractedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> ExtractedLibraryData:
        """Send the transcript to the LLM and parse its findings."""
        data = self.get_data()
        series = data.series
        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()
        try:
            report_progress(0, 1, "Scanning subtitle file for characters and terms", 0.0)
            raw = llm.infer(
                prompt=data.transcript,
                system_prompt=scan_subtitle_file_prompt(
                    series["name"], series["input_lang"], series["output_lang"], data.known_names, data.known_terms,
                ),
                temperature=0.1,
            )
        finally:
            model_manager.release_llm()

        findings = self._parse_findings(raw)
        write_log("01-scan-subtitle-file.json", {"raw_output": raw, "findings": findings.to_log()})
        report_progress(1, 1, f"Found {len(findings.characters)} characters, {len(findings.terms)} terms", 0.0)
        return extend(data, ExtractedLibraryData, findings=findings)

    def _parse_findings(self, raw: str) -> Findings:
        """Parse the LLM's JSON findings; raises ValueError on malformed output."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            return Findings(
                characters=[str(c) for c in parsed.get("characters", [])],
                terms=[str(t) for t in parsed.get("terms", [])],
                events=[str(e) for e in parsed.get("events", [])],
            )
        except Exception as exc:
            raise ValueError(f"{self.task_type}: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

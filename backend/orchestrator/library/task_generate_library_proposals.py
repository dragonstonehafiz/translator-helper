import json

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import extend
from orchestrator.task_data.library_update import CharacterUpdateProposal, LibraryProposals, ProposedLibraryData, SearchedLibraryData
from prompts.library import generate_library_proposals_prompt

VALID_CHARACTER_UPDATE_FIELDS = {"personality", "relationships", "history"}


class TaskGenerateLibraryProposals(BaseTask[SearchedLibraryData, ProposedLibraryData]):
    """Library update stage 5: propose new and updated characters and glossary terms."""

    input_type = SearchedLibraryData
    output_type = ProposedLibraryData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> ProposedLibraryData:
        """Build the prompt from the transcript, the library and any search results, then parse the proposals."""
        data = self.get_data()
        series = data.series
        known = {"characters": data.known.characters, "terms": data.known.terms}
        prompt_parts = [
            f"=== SUBTITLE FILE ===\n{data.transcript}",
            f"\n=== EXISTING LIBRARY ===\n{json.dumps({'characters': series['characters'], 'glossary': series['glossary']}, ensure_ascii=False, indent=2)}",
            f"\n=== ALREADY KNOWN (do not re-add) ===\n{json.dumps(known, ensure_ascii=False)}",
        ]
        if data.search_results:
            prompt_parts.append(f"\n=== WEB SEARCH RESULTS ===\n{json.dumps(data.search_results, ensure_ascii=False, indent=2)}")

        model_manager = ModelManager.get_instance()
        llm = model_manager.get_llm_client()
        report_progress(0, 1, "Generating library update proposals", 0.0)
        raw = llm.infer(
            prompt="\n".join(prompt_parts),
            system_prompt=generate_library_proposals_prompt(series["name"], series["input_lang"], series["output_lang"]),
            temperature=0.2,
        )

        proposals = self._parse_proposals(raw)
        write_log("05-generate-library-proposals.json", {"raw_output": raw, "proposals": proposals})
        report_progress(1, 1, "Proposals generated", 0.0)
        return extend(data, ProposedLibraryData, proposals=proposals)

    def _parse_proposals(self, raw: str) -> LibraryProposals:
        """Parse the proposals JSON, keeping only character updates to personality, relationships or history."""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            parsed = json.loads(text)
            return {
                "new_characters": parsed.get("new_characters", []),
                "updated_characters": [
                    self._character_update(u) for u in parsed.get("updated_characters", [])
                    if isinstance(u, dict) and u.get("field") in VALID_CHARACTER_UPDATE_FIELDS
                ],
                "new_glossary": parsed.get("new_glossary", []),
                "updated_glossary": parsed.get("updated_glossary", []),
            }
        except Exception as exc:
            raise ValueError(f"{self.task_type}: failed to parse LLM output as JSON. Raw output:\n{raw}") from exc

    @staticmethod
    def _character_update(update: dict) -> CharacterUpdateProposal:
        """Keep a character update's id, field, append text and, for relationships, the other character's name."""
        proposal: CharacterUpdateProposal = {
            "id": str(update.get("id", "")),
            "field": str(update["field"]),
            "append": str(update.get("append", "")),
        }
        if "character" in update:
            proposal["character"] = str(update["character"])
        return proposal

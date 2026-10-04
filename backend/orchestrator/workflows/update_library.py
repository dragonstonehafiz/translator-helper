from pathlib import Path

from orchestrator.library.task_classify_library_findings import TaskClassifyLibraryFindings
from orchestrator.library.task_deduplicate_character_updates import TaskDeduplicateCharacterUpdates
from orchestrator.library.task_extract_library_findings import TaskExtractLibraryFindings
from orchestrator.library.task_generate_library_proposals import TaskGenerateLibraryProposals
from orchestrator.library.task_generate_search_queries import TaskGenerateSearchQueries
from orchestrator.library.task_web_search import TaskWebSearch
from orchestrator.task_data.base import TaskData
from orchestrator.task_data.library_types import SeriesSnapshot
from orchestrator.task_data.library_update import LibraryUpdateData, ProposalOutputData, ProposedLibraryData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.workflows import remove_files
from utils.subtitles import load_subtitles, speaker_lines

WORKFLOW = "update_library"


def start_update_library(file_path: Path, input_filename: str, series: SeriesSnapshot) -> None:
    """Load the subtitles once, then start proposing library additions; the temp file is deleted when the run ends."""
    known_names: list[str] = []
    for char in series["characters"]:
        known_names.append(char["name"])
        known_names.extend(char.get("aliases", []))
    data = LibraryUpdateData(
        series=series,
        transcript="\n".join(speaker_lines(load_subtitles(str(file_path)))),
        known_names=known_names,
        known_terms=[term["term"] for term in series["glossary"]],
        input_filename=input_filename,
    )
    tasks = [
        TaskExtractLibraryFindings(),
        TaskClassifyLibraryFindings(),
        TaskGenerateSearchQueries(),
        TaskWebSearch(),
        TaskGenerateLibraryProposals(),
        TaskDeduplicateCharacterUpdates(),
    ]
    TaskOrchestrator.get_instance().run(WORKFLOW, tasks, data, finish=_finish, cleanup=remove_files(file_path))


def _finish(data: TaskData) -> ProposalOutputData:
    """Keep only the deduplicated proposals as the result."""
    if not isinstance(data, ProposedLibraryData):
        raise TypeError(f"{WORKFLOW} finish expects ProposedLibraryData, got {type(data).__name__}.")
    return ProposalOutputData(proposals=data.proposals)

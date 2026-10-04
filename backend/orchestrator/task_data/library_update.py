"""Data for the update_library workflow, including the proposal shapes the Library page reviews."""

from dataclasses import dataclass
from typing import NotRequired, TypedDict

from orchestrator.task_data.base import TaskData
from orchestrator.task_data.library_types import SeriesSnapshot


@dataclass(kw_only=True)
class Findings:
    """Character names, terms and events mentioned in a subtitle file."""

    characters: list[str]
    terms: list[str]
    events: list[str]

    def to_log(self) -> dict[str, list[str]]:
        """Return the findings as a JSON-ready dict."""
        return {"characters": self.characters, "terms": self.terms, "events": self.events}


class SearchQuery(TypedDict):
    """One web search to run for an unknown name or term."""

    subject: str
    query: str


class SearchResult(TypedDict):
    """Snippets returned for one search subject."""

    subject: str
    results: list[str]


class NewCharacterProposal(TypedDict):
    """A proposed new character."""

    name: str
    aliases: list[str]
    personality: list[str]
    relationships: dict[str, list[str]]
    history: list[str]


class CharacterUpdateProposal(TypedDict):
    """A fact to append to an existing character; `character` is set only for relationship additions."""

    id: str
    field: str
    append: str
    character: NotRequired[str]


class NewGlossaryProposal(TypedDict):
    """A proposed new glossary term."""

    term: str
    translation: str
    notes: str


class GlossaryUpdateProposal(TypedDict):
    """A proposed change to one field of an existing glossary term."""

    id: str
    field: str
    value: str


class LibraryProposals(TypedDict):
    """The four proposal categories the Library page reviews."""

    new_characters: list[NewCharacterProposal]
    updated_characters: list[CharacterUpdateProposal]
    new_glossary: list[NewGlossaryProposal]
    updated_glossary: list[GlossaryUpdateProposal]


@dataclass(kw_only=True)
class LibraryUpdateData(TaskData):
    """Prepared input of a library update."""

    series: SeriesSnapshot
    transcript: str
    known_names: list[str]
    known_terms: list[str]
    input_filename: str

    def run_label(self) -> str | None:
        """Use the uploaded filename for the log folder."""
        return self.input_filename


@dataclass(kw_only=True)
class ExtractedLibraryData(LibraryUpdateData):
    """Library update data with the names, terms and events found in the file."""

    findings: Findings


@dataclass(kw_only=True)
class ClassifiedLibraryData(ExtractedLibraryData):
    """Findings split into those already in the library and those that are not."""

    known: Findings
    unknown: Findings


@dataclass(kw_only=True)
class QueriedLibraryData(ClassifiedLibraryData):
    """Library update data with the web searches to run (possibly none)."""

    search_queries: list[SearchQuery]


@dataclass(kw_only=True)
class SearchedLibraryData(QueriedLibraryData):
    """Library update data with the web search results (possibly none)."""

    search_results: list[SearchResult]


@dataclass(kw_only=True)
class ProposedLibraryData(SearchedLibraryData):
    """Library update data with the generated proposals."""

    proposals: LibraryProposals


@dataclass(kw_only=True)
class ProposalOutputData(TaskData):
    """Final result of a library update."""

    proposals: LibraryProposals

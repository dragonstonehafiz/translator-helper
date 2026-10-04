"""Shapes of the series library JSON, used by translation context selection and library updates."""

from typing import TypedDict


class CharacterEntry(TypedDict):
    """A character as stored in characters.json."""

    id: str
    name: str
    aliases: list[str]
    personality: list[str]
    relationships: dict[str, list[str]]
    history: list[str]


class GlossaryEntry(TypedDict):
    """A glossary term as stored in glossary.json."""

    id: str
    term: str
    translation: str
    notes: str


class SeriesSnapshot(TypedDict):
    """A full series as returned by library.repository.load_series."""

    id: str
    name: str
    input_lang: str
    output_lang: str
    notes: str
    characters: list[CharacterEntry]
    glossary: list[GlossaryEntry]


class LibraryContext(TypedDict):
    """Library entries selected as relevant for one subtitle file."""

    selected_characters: list[CharacterEntry]
    selected_glossary: list[GlossaryEntry]

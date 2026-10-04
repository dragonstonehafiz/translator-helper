"""Output naming and saving shared by the file-producing workflows."""

import os
from pathlib import Path

import pysubs2

from utils.config import OUTPUTS_DIR


def _safe_lang(language: str) -> str:
    """Keep only letters, digits, '-' and '_' from a language code, falling back to 'lang'."""
    return "".join(char for char in language if char.isalnum() or char in ("-", "_")) or "lang"


def translated_filename(original_filename: str, output_lang: str) -> str:
    """Return <first filename segment>.<language>.<original extension>."""
    name_parts = os.path.basename(original_filename).split(".")
    return f"{name_parts[0]}.{_safe_lang(output_lang)}.{name_parts[-1]}"


def reviewed_filename(translated_filename: str) -> str:
    """Return <translated stem>.corrected<suffix>, using .ass when the name has no suffix."""
    path = Path(os.path.basename(translated_filename) or "translated.ass")
    return f"{path.stem}.corrected{path.suffix or '.ass'}"


def transcribed_filename(original_filename: str, language: str) -> str:
    """Return <first filename segment>.<language>.ass."""
    return f"{os.path.basename(original_filename).split('.')[0]}.{_safe_lang(language)}.ass"


def save_subtitles(subtitles: pysubs2.SSAFile, folder: str, filename: str) -> Path:
    """Save subtitles to OUTPUTS_DIR/<folder>/<filename>, replacing any existing file, and return the path."""
    output_dir = OUTPUTS_DIR / folder
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    subtitles.save(str(output_path))
    return output_path

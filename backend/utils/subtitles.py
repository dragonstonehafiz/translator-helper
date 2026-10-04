"""Subtitle loading, formatting and statistics helpers."""

import pysubs2


def load_subtitles(file_path: str) -> pysubs2.SSAFile:
    """Load a subtitle file, raising ValueError when it contains no subtitle lines."""
    subs = pysubs2.load(file_path)
    if len(subs) == 0:
        raise ValueError("Subtitle file does not contain any subtitle lines.")
    return subs


def speaker_lines(subs: pysubs2.SSAFile) -> list[str]:
    """Return each line as 'Speaker: text', the transcript form used by the library prompts."""
    return [f"{line.name}: {line.text}" for line in subs]


def numbered_lines(subs: pysubs2.SSAFile, start: int = 1, end: int | None = None) -> list[str]:
    """Return lines start..end (1-based, inclusive) as '1. Speaker: text', with 'Unknown' and '[EMPTY]' placeholders."""
    last = len(subs) if end is None else end
    lines = []
    for index in range(start, last + 1):
        line = subs[index - 1]
        speaker = line.name.strip() if line.name else "Unknown"
        text = line.text.strip() or "[EMPTY]"
        lines.append(f"{index}. {speaker}: {text}")
    return lines


def analyze_subtitle_file(file_path: str) -> dict[str, str]:
    """Return dialogue stats for an ASS/SRT subtitle file."""
    subs = pysubs2.load(file_path)
    total_lines = 0
    total_characters = 0
    for event in subs.events:
        text = event.plaintext.strip()
        if not text:
            continue
        speaker = event.name.strip() if event.name else ""
        line_text = f"{speaker}: {text}" if speaker else text
        total_lines += 1
        total_characters += len(line_text)

    average_characters = total_characters / total_lines if total_lines else 0
    return {
        "total_lines": str(total_lines),
        "character_count": str(total_characters),
        "average_character_count": f"{average_characters:.2f}",
    }

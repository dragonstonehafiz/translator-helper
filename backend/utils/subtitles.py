"""Subtitle loading and statistics helpers."""

import pysubs2


def load_sub_data(filepath: str, include_speaker: bool = True) -> list[str]:
    """Load a subtitle file and return each line as a plain string, optionally prefixed with the speaker name."""
    subs = pysubs2.load(filepath)
    output_list = []
    for line in subs:
        line: pysubs2.SSAEvent
        if include_speaker:
            text = f"{line.name}: {line.text}"
        else:
            text = line.text
        output_list.append(text)

    return output_list


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

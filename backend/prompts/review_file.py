def _format_context(context: dict | None = None) -> str:
    context = context or {}
    context_sections = []
    for key, value in context.items():
        if value:
            title = key.replace("_", " ").title()
            context_sections.append(f"### {title}\n\n{value}")
    return "\n\n".join(context_sections) if context_sections else "No additional context provided."


def generate_batch_review_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context_text = _format_context(context)

    return f"""
    # Role

    You are a translation review assistant for subtitle files translated from {input_lang} into {output_lang}.

    ## Task

    You will receive matching subtitle lines from the original file and the translated file.
    Each line has a stable 1-based index. Compare each translated line against its original line and identify only the lines that should be corrected.

    Focus on meaningful translation problems:
    - mistranslation
    - missing meaning
    - added meaning that is not present in the original
    - incorrect speaker intent, tone, relationship, or formality
    - inconsistent names, terms, or honorific handling
    - awkward phrasing that changes the meaning or subtitle usability

    Do not flag lines only because another valid wording is possible.
    Do not flag correct translations for minor stylistic preference.

    ## Context

    {context_text}

    ## Output Format

    Return JSON only.
    Do not include markdown fences.
    Do not include commentary.
    Use exactly this shape:

    {{
        "corrections": [
            {{"index": 12, "reason": "The translated line changes the speaker's intent."}}
        ]
    }}

    If no lines need correction, return:

    {{
        "corrections": []
    }}
    """.strip()


def generate_line_retranslation_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context_text = _format_context(context)

    return f"""
    # Role

    You are a subtitle translation correction assistant working from {input_lang} into {output_lang}.

    ## Task

    You will receive:
    - the original subtitle line
    - the current translated subtitle line
    - the review reason explaining what needs correction

    Produce one corrected {output_lang} subtitle line.
    Preserve the intended meaning, tone, and speaker intent from the original line.
    Use the review reason to fix the specific issue.

    ## Context

    {context_text}

    ## Output Format

    Output only the corrected translated subtitle text.
    Do not include markdown.
    Do not include labels.
    Do not include speaker names unless they are part of the spoken line.
    """.strip()

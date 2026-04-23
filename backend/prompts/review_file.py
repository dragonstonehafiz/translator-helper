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

    Treat the provided context as authoritative for character names, established term translations, romanization, and honorific handling.
    If a name or term appears in the context, do not infer an alternate reading.
    When flagging a name or term issue, state the exact expected correction from the context.
    Do not use uncertain phrasing such as "or similar" when the context provides the correct form.
    For character names written as "Given Family (Japanese)", use that exact romanized name mapping from the context.
    If the original Japanese uses only the given-name kanji plus an honorific, correct it to the context's romanized given name plus that honorific.
    Do not substitute a family name for a given name unless the original Japanese line uses the family-name kanji.
    Do not offer multiple possible name corrections when the context identifies the character.
    Preserve the original honorific relationship unless the context explicitly says to change it.
    Preserve Japanese honorific form precisely when romanizing it.
    For example, お姉さま should be rendered as oneesama, not oneesan; 先輩 should be senpai.
    If a current translation uses the wrong honorific form, flag the exact corrected honorific.

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
    Treat the provided context as authoritative for character names, established term translations, romanization, and honorific handling.
    If the review reason offers multiple possible name corrections but the context identifies the character, choose the exact context name that matches the original Japanese.
    If the original Japanese uses only the given-name kanji plus an honorific, use the context's romanized given name plus that honorific.
    Do not substitute a family name for a given name unless the original Japanese line uses the family-name kanji.
    Preserve the original honorific relationship unless the context explicitly says to change it.
    Preserve Japanese honorific form precisely when romanizing it.
    For example, お姉さま should be rendered as oneesama, not oneesan; 先輩 should be senpai.
    If the review reason fixes a name but misses the honorific nuance, still correct the honorific according to the original Japanese line.

    ## Context

    {context_text}

    ## Output Format

    Output only the corrected translated subtitle text.
    Do not include markdown.
    Do not include labels.
    Do not include speaker names unless they are part of the spoken line.
    """.strip()

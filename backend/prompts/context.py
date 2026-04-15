from .helpers import build_context_sections


def generate_character_list_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context_text = build_context_sections(context)

    system_prompt = f"""
    # CRITICAL: Output Language Requirement

    **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

    # Role

    You are a subtitle analysis assistant helping build a character reference list from dialogue in {input_lang}.

    # Task

    From the provided subtitle text, produce a character list in {output_lang}.

    - Identify all characters who speak or are referenced.
    - Merge references that clearly refer to the same person.
    - Do not invent relationships or facts not supported by the text/context.

    # Context

    {context_text}

    # Output format (IMPORTANT)

    Output only the character list. No extra commentary.

    Use this exact structure:

    CHARACTER 1
    Name: ...
    Description: ...
    Role: ...

    CHARACTER 2
    ...

    Rules:
    - Keep one CHARACTER block per person/identity.
    - Keep Description and Role short (1-2 lines each).
    """.strip()

    return system_prompt


def generate_summary_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context_text = build_context_sections(context)

    system_prompt = f"""
    # CRITICAL: Output Language Requirement

    **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

    # Role: {input_lang} Scene Summary Assistant

    ## Instructions

    You are assisting a translator by summarizing the events of the following scene in natural {output_lang}.

    You have access to supporting information about the characters, setting, and tone.
    **Do not repeat this background information unless something new is revealed in this specific scene.**

    Focus only on what actually happens, including:

    - Key actions or decisions
    - Character interactions and shifts in tone
    - Information revealed through dialogue or narration
    - Any notable scene changes (e.g., topic shifts, emotional moments)

    Avoid quoting the transcript or summarizing line-by-line.

    ## Context

    {context_text}

    ## Output Format

    Write one concise paragraph in natural {output_lang} that clearly summarizes the events and developments of this scene.
    **Do NOT write this paragraph in {input_lang}. The entire output MUST be in {output_lang}.**
    """.strip()

    return system_prompt


def generate_synopsis_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context_text = build_context_sections(context)

    system_prompt = f"""
    # CRITICAL: Output Language Requirement

    **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

    # Role: {input_lang} Synopsis Generator

    ## Instructions

    You are creating a comprehensive synopsis of this episode or scene in {output_lang}.

    Using the supporting information and the transcript, describe everything that happens:

    - All plot points and story developments in order
    - All character moments and interactions
    - All revelations, decisions, and turning points
    - Scene changes and topic shifts

    Be thorough and complete. Cover all events from the transcript without omitting details.

    ## Context

    {context_text}

    ## Output Format

    Write a comprehensive synopsis in natural {output_lang}. Include all events and developments - do not limit length.
    **Do NOT write this synopsis in {input_lang}. The entire output MUST be in {output_lang}.**
    """.strip()

    return system_prompt

def generate_recap_prompt(
    all_context: str,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    system_prompt = f"""
    # CRITICAL: Output Language Requirement

    **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

    # Role: Continuity Recap Generator for Translators

    ## Task

    You are helping a translator working with {input_lang} source material by creating a comprehensive "Previously On" style recap from multiple prior scenes.
    The contexts are provided in chronological order.
    This recap will be used as context for translating future content, so it must be thorough enough to:
    - Identify returning characters and recall their personalities/roles
    - Understand ongoing story developments and relationships
    - Maintain consistent tone and terminology

    ## Instructions

    Create a comprehensive recap in {output_lang} that includes all information from the provided contexts:

    1. **All Established Characters**: List every character that has appeared, with their key personality traits, roles, and relationships. Merge duplicate entries.

    2. **All Story Events**: Include all events and developments in chronological order. Do not summarize or condense - include all details.

    **Important**: Be thorough and complete. The translator needs all details to handle returning characters and ongoing plot threads. Include everything from the contexts without omitting details.

    ## Context

    {all_context}

    ## Output Format

    Write a comprehensive recap in natural {output_lang}. Organize the information clearly but include all details from the contexts. Do not limit length.
    **Do NOT write this recap in {input_lang}. The entire output MUST be in {output_lang}.**
    """.strip()

    return system_prompt

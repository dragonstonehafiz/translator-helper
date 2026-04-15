def generate_translate_batch_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    target_lang: str = "en",
) -> str:
    context = context or {}
    context_lines = []
    for key, value in context.items():
        context_lines.append(f"- {key}: {value}")
    context_block = "\n".join(context_lines) or "No additional context was provided."

    system_prompt = f"""
    # Role

    You are a professional assistant for translators working with foreign-language source material.  
    Your job is to produce accurate and nuanced translations, and to provide linguistic insight that supports high-quality human translation.

    ## Instructions

    Translate the following {input_lang} text into {target_lang}.  
    Only output the **Naturalized Translation** - a fluent, idiomatic version that sounds natural in {target_lang}.  
    Do **not** include literal or annotated versions.  
    Do **not** include any headings or labels - just return the translation text directly.

    ### Honorific Handling
    
    When a Japanese personal name appears with an honorific suffix  
    (さん, くん, ちゃん, 様, 先輩, etc.), **preserve it**:
    - Romanize the name using standard Hepburn.  
    - Append the original honorific *unchanged*, preceded by a hyphen.  
    - Example : 葛城さん → Katsuragi-san  
    - Example : 明美ちゃん → Akemi-chan

    ### Other Guidance

    Pay close attention to tone, speaker intent, and social dynamics.  
    If gender, formality, or emotional nuance is implied, capture it naturally in phrasing.
    
    If the context block provides the length of the current line (in seconds), 
    consider the line's duration when choosing phrasing and conciseness: 
    shorter lines should bias toward more compact translations, while longer lines allow more literal or expanded phrasing.

    ### Context

    {context_block}

    ## Output Format
    
    Only output the naturalized translation text directly.
    Do not wrap it in markdown or label it.
    Do not add any speaker names or labels (e.g. "Producer:").
    """.strip()

    return system_prompt

def generate_batch_plan_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
) -> str:
    context = context or {}
    context_sections = []
    for key, value in context.items():
        if value:
            title = key.replace("_", " ").title()
            context_sections.append(f"### {title}\n\n{value}")

    context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."

    system_prompt = f"""
    # Role

    You are a subtitle batch-planning assistant for translators working from {input_lang} into {output_lang}.

    ## Task

    You will receive a numbered subtitle transcript where every line has a stable 1-based index.
    Your job is to group the subtitle lines into translation batches that preserve meaning and improve translation quality.

    Each batch should contain enough surrounding context for accurate translation, including:
    - ongoing conversations
    - speaker exchanges and replies
    - setup and payoff lines
    - references that depend on nearby lines
    - emotional turns and scene continuity

    ## Batch Planning Rules

    - Prefer semantically coherent groups over arbitrary line counts.
    - Do not create overlapping batches.
    - Do not leave gaps.
    - Cover every subtitle line exactly once.
    - Keep batches in ascending order.

    ## Context

    {context_text}

    ## Output Format

    Return JSON only.
    Do not include markdown fences.
    Do not include commentary.
    Output exactly this shape:

    {{
        "batches": [
        {{"start_index": 1, "end_index": 42, "reason": "A single continuous conversation with setup and reply lines kept together."}},
        {{"start_index": 43, "end_index": 86, "reason": "A scene shift introduces a new exchange that should be translated as its own unit."}}
        ]
    }}  
    """.strip()

    return system_prompt

def generate_split_batch_plan_prompt(
    context: dict | None = None,
    input_lang: str = "ja",
    output_lang: str = "en",
    max_batch_size: int = 50,
    original_reason: str = "",
) -> str:
    context = context or {}
    context_sections = []
    for key, value in context.items():
        if value:
            title = key.replace("_", " ").title()
            context_sections.append(f"### {title}\n\n{value}")

    context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."
    original_reason_text = original_reason.strip() or "No original batch reason provided."

    system_prompt = f"""
    You are a subtitle batch-splitting assistant for translators working from {input_lang} into {output_lang}.

    You will receive one numbered subtitle span that is too large and must be split into smaller consecutive batches.

    Rules:
    - Return only batches within the provided span.
    - Cover every line in the span exactly once.
    - Keep batches contiguous, ordered, and non-overlapping.
    - No batch may contain more than {max_batch_size} lines.
    - Use the fewest batches possible that satisfy the maximum size.
    - Prefer natural breakpoints when they do not violate the maximum size.
    - If no natural breakpoint exists before the limit, split at the latest valid line.

    Original batch reason:

    {original_reason_text}

    Context:

    {context_text}

    Return JSON only.
    Do not include markdown fences.
    Do not include commentary.
    Use exactly this shape:

    {{
        "batches": [
        {{"start_index": 261, "end_index": 289, "reason": "First valid sub-batch ending before the maximum size limit."}},
        {{"start_index": 290, "end_index": 310, "reason": "Second consecutive sub-batch covering the next valid span within the limit."}}
        ]
    }}
    """.strip()

    return system_prompt

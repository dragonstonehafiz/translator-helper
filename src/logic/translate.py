from langchain_core.messages import SystemMessage, HumanMessage

def translate(llm, text: str, context: dict = None,
              input_lang: str = "ja", target_lang: str = "en") -> str:
    """
    Perform structured translation using a LangChain ChatOpenAI model.

    Parameters:
    - llm: LangChain ChatOpenAI instance
    - text: Source language input
    - context: Optional dict of context information (e.g., scene_structure, characters, tone)
    - input_lang: Source language code (default 'ja')
    - target_lang: Target language code (default 'en')

    Returns:
    - A markdown-formatted translation response as a string
    """

    context_lines = []
    for key, value in context.items():
        context_lines.append(f"- {key}: {value}")
    context_block = "\n".join(context_lines) or "No additional context was provided."

    system_prompt = f"""
    # Role

    You are a professional assistant for translators working with foreign-language source material.  
    Your job is to produce accurate and nuanced translations, and to provide linguistic insight that supports high-quality human translation.

    ## Instructions

    Translate the following {input_lang} text into {target_lang}, and provide three versions:

    1. **Naturalized Translation** — a fluent, idiomatic version that sounds natural in {target_lang}.  
    2. **Literal Translation** — a direct, word-for-word rendering that reflects the structure and phrasing of the original {input_lang}.  
    3. **Annotated Translation** — a readable version that includes notes on idioms, grammar particles, honorifics, cultural references, or any challenging phrases. Notes can be inline (in parentheses) or listed as footnotes.

    Pay close attention to tone, speaker intent, and social dynamics.  
    If gender, formality, or emotional nuance is implied, capture it in the annotations.

    ### Context

    {context_block}

    ## Output Format

    Respond in markdown with this format:

    **Naturalized Translation**  
    [text]

    **Literal Translation**  
    [text]

    **Annotated Translation**  
    [text with notes]
    """.strip()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text.strip())
    ]

    response = llm.invoke(messages)
    return response.content

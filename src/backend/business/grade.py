from langchain_core.messages import SystemMessage, HumanMessage

def grade(llm, original_text: str, translated_text: str, context: dict = None,
          input_lang: str = "ja", target_lang: str = "en") -> str:
    """
    Evaluate a translation using a LangChain-compatible LLM.

    Parameters:
    - llm: LangChain ChatOpenAI instance
    - original_text: Source text in input_lang
    - translated_text: Translated text in target_lang
    - context: Optional dictionary with scene information (tone, characters, etc.)
    - input_lang: Language of the source text
    - target_lang: Language of the translation

    Returns:
    - A markdown-formatted evaluation string
    """

    context_lines = []
    for key, value in context.items():
        context_lines.append(f"- {key}: {value}")
    context_block = "\n".join(context_lines) or "No additional context was provided."

    system_prompt = f"""
    # Role: {input_lang}-to-{target_lang} Translation Evaluator

    ## Instructions

    You are a professional translation evaluator with expertise in:
    - fidelity to the source,
    - fluency of the output, and
    - appropriate cultural localization.

    Evaluate the translation in terms of:

    - **Accuracy** — Faithfulness to the original meaning.  
    - **Fluency** — Natural, grammatical {target_lang}.  
    - **Cultural Appropriateness** — Sensitivity to nuance, setting, and audience expectations.  

    ## Context

    {context_block}

    ## Output Format

    **Average Score**: X.X

    **Accuracy**: [score] – [reason]  
    **Fluency**: [score] – [reason]  
    **Cultural Appropriateness**: [score] – [reason]  

    **Suggestions for Improvement**:
    - Suggestion 1  
    - Suggestion 2  
    - Suggestion 3  

    **Notable Issues** (optional):
    - Example: “X” could be misread as Y.
    """.strip()
    
    human_prompt = f"""
    ## Original Text ({input_lang})
    
    {original_text}
    
    ## Translated Text ({target_lang})
    
    {translated_text}
    
    """.strip()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    response = llm.invoke(messages)
    return response.content

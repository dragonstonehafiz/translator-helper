from langchain_core.messages import SystemMessage, HumanMessage
from pysubs2.ssafile import SSAFile
from langchain_openai import ChatOpenAI
from tqdm import tqdm

def translate_multi_response(llm: ChatOpenAI, text: str, context: dict = None,
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


def translate_sub(llm: ChatOpenAI, text: str, context: dict = None,
                  input_lang: str = "ja", target_lang: str = "en"):
    
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
    Only output the **Naturalized Translation** — a fluent, idiomatic version that sounds natural in {target_lang}.  
    Do **not** include literal or annotated versions.  
    Do **not** include any headings or labels — just return the translation text directly.

    Pay close attention to tone, speaker intent, and social dynamics.  
    If gender, formality, or emotional nuance is implied, capture it naturally in phrasing.

    ### Context

    {context_block}

    ## Output Format

    Only output the naturalized translation text directly.
    Do not wrap it in markdown or label it.
    If there is indicator of the speaker (i.e. "Speaker1: blah blah blah"), remove the indicator
    """.strip()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text.strip())
    ]

    response = llm.invoke(messages)
    return response.content.strip()


def translate_subs(llm: ChatOpenAI, subs, context: dict, context_window: int = 3,
                   input_lang: str = "ja", target_lang: str = "en") -> SSAFile:
    
    
    for idx, line in enumerate(tqdm(subs, desc="Translating Lines", unit="line")):
        
        # Take the lines before and after this current line to help with translation
        prev_lines = subs[max(0, idx - context_window):idx]
        next_lines = subs[idx + 1:idx + context_window + 1]
        
        # Make a copy of the context dict, and add the previous and after lines
        context_dict = context.copy()
        context_dict["Previous Lines"] = "\n".join([f"{l.name}: {l.text}" for l in prev_lines])
        context_dict["Next Lines"] = "\n".join([f"{l.name}: {l.text}" for l in next_lines])
        context_dict["Current Speaker"] = line.name
        
        current_line = f"{line.text}"
        translation = translate_sub(llm, current_line, context=context_dict,
                                       input_lang=input_lang, target_lang=target_lang)
        
        line.text = translation
        
    return subs
        
        
        
    
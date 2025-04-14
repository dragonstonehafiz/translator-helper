from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableMap, RunnableLambda
from langchain_community.tools.tavily_search.tool import TavilySearchResults


def determine_scene_structure(model: ChatOpenAI, input_lang: str, output_lang: str, transcript: str):
    prompt = """
    # Role: {input_lang} Scene Structure Assistant

    ## Instructions

    Examine the text and describe the **structure and delivery format** in natural {output_lang}.  
    Focus on **how the dialogue is organized**, and whether characters are interacting or delivering isolated lines.

    ### Important

    - Do **not** assume a conversation simply because multiple speaker names appear.
    - Only classify the scene as interactive *if the characters are clearly responding to each other’s lines*.
    - If each speaker talks independently, without responding to others, treat it as a sequence of monologues.

    ### What to Include

    Use the following labeled format in your output for clarity:

    **Scene Type**: [e.g., Interactive Dialogue / Monologue / Narration / Mixed]  
    **Speaker Count**: [e.g., 1, 2, 3+, or "Unclear"]  
    **Interaction Style**: [Describe whether speakers engage with each other or not]  
    **Delivery Format**: [e.g., Speaker-separated entries, Timestamped logs, Introspective monologue]  
    **Notes**: [Any other relevant structural observations]

    ### Transcript

    {scene_text}

    ## Output Format

    Return your answer in the labeled format above using **bold markdown headers** (e.g., **Scene Type**).  
    Keep each line concise and easy to scan. Only state what is directly observable in the dialogue.
    """

    analyze_format_prompt = ChatPromptTemplate.from_template(prompt)
    analyze_format_chain = (
        RunnableMap({
            "scene_text": lambda x: x["text"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
        }) | analyze_format_prompt | model
    )
    
    result = analyze_format_chain.invoke({
        "text": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang
    })

    return result.content


def gather_context_from_web(model: ChatOpenAI, search_tool: TavilySearchResults, output_lang: str, 
                            series_name: str, keywords: str):
    web_context_prompt_str = """
    # Role: Translator Support Assistant

    ## Instructions

    You are assisting a translator working on a project involving the series titled **{series_name}**.  
    The user has also provided the following keywords to guide your understanding: **{keywords}**.

    Use the search results below to construct a helpful, factual background summary in natural {output_lang}.  
    Only use information that is present in the search results. Do **not** speculate, interpret tone, or invent missing details.

    ### Important

    - Do **not** include personal opinions or unverified claims.
    - If the retrieved content is ambiguous or incomplete, acknowledge it briefly.
    - Focus on surface-level, factual context that can support a translator's understanding of the setting, characters, or themes.

    ### What to Include

    - The general premise and genre of the series (if stated).
    - A summary of the setting or overall structure (e.g., school mystery, fantasy world, time period).
    - A list or brief mention of recurring characters (if available).
    - Any relevant details about themes, tone, format, or social context relevant to translation decisions.

    ### Search Results

    {search_results}

    ## Output Format

    Write a clearly formatted summary in natural {output_lang} using **bolded section labels** followed by a colon.  
    Each labeled section (e.g., **Premise and Genre:**) should be on its own line, but **do not use bullet points or lists**.  
    Keep each section to no more than 2 sentences, and use **no more than 6 labeled sections** in total.
    """

    web_context_prompt = ChatPromptTemplate.from_template(web_context_prompt_str)
    web_context_chain = (
        RunnableLambda(lambda x: {
            "series_name": x["series_name"],
            "keywords": x["keywords"],
            "output_lang": x["output_lang"],
            "query": f"{x['series_name']} {x['keywords']}",
            "search_results": search_tool.invoke({"query": f"{x['series_name']} {x['keywords']}"})
        })
        | web_context_prompt
        | model
    )
    
    result = web_context_chain.invoke({
        "series_name": series_name,
        "keywords": keywords,
        "output_lang": output_lang
    })
    
    return result.content


def identify_characters(model: ChatOpenAI, input_lang: str, output_lang: str, transcript: str, 
                        format_description: str = None, web_context: str = None):
    prompt_str = """
    # Role: {input_lang} Character Identifier
    
    ## Input
    
    ### Web Context

    {web_notes}

    ### Transcript

    {scene_text}
    
    ### Format Description
    
    {format_notes}

    ## Instructions

    You are assisting a translator by identifying characters in a scene.  
    Use the dialogue transcript to extract any named or inferred characters.  

    For each character:
    - Provide their **name**
    - Describe any **traits or roles** that are *clearly observable* (e.g., casual tone, teacher, narrator)
    - If one character is **clearly the narrative focus** (appears most, drives the scene), add **[Narrative Focus]**

    Do **not** speculate. Only use information grounded in the transcript or search context.

    ## Output Format

    Return a list in this format:
    - **[Character Name]**: [brief description]. [Narrative Focus] (if applicable)

    Include only one entry per character. Format the name in bold using markdown (** **).
    """

    format_notes = (
        f"Consider the following format when interpreting the structure:\n{format_description}"
        if format_description else "No specific format description is provided."
    )

    web_notes = (
        "You may refer to the following background information to improve accuracy." 
        if web_context else "No external series information was provided."
    )

    final_prompt = ChatPromptTemplate.from_template(prompt_str)

    character_chain = (
        RunnableMap({
            "scene_text": lambda x: x["text"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "format_notes": lambda x: x["format_notes"],
            "web_notes": lambda x: x["web_notes"]
        }) | final_prompt | model
    )

    result = character_chain.invoke({
        "text": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "format_notes": format_notes,
        "web_notes": web_notes
    })

    return result.content


def summarize_scene(model: ChatOpenAI, input_lang: str, output_lang: str, transcript: str, 
                    format_description: str = None, character_list: str = None, web_context: str = None):
    prompt_str = """
    # Role: {input_lang} Scene Summary Assistant

    ## Input

    ### Web Context

    {web_notes}

    ### Transcript

    {scene_text}

    ### Format Description

    {format_notes}

    ### Characters

    {character_notes}

    ## Instructions

    You are assisting a translator by providing a high-level summary of the following scene in natural {output_lang}.  
    Your goal is to help the translator understand the context *before* they begin translating.  

    Focus on the **location**, **involved characters**, and **key actions or themes** of the scene.  
    Avoid retelling the dialogue line-by-line or interpreting character emotions.

    ## Output Format

    Structure your output into labeled sections for readability:

    **Setting**: [Where the scene takes place and any notable environmental context]  
    **Main Characters**: [Who is involved and their roles or relationships]  
    **Situation**: [What is happening in broad terms — discussion, conflict, action, etc.]  
    **Themes**: [Any recurring or prominent ideas mentioned — e.g., power, family, ideology]

    Write clearly and concisely. Use full sentences, but keep each section focused and skimmable.
    """
    
    # Optional inserts
    format_notes = f"Consider the following scene structure:\n{format_description}" if format_description else "No scene structure provided."
    character_notes = f"The following characters were identified:\n{character_list}" if character_list else "No characters were identified."
    web_notes = f"You may also refer to the following background information:\n{web_context}" if web_context else "No external series information provided."

    summarize_prompt = ChatPromptTemplate.from_template(prompt_str)

    summarize_chain = (
        RunnableMap({
            "scene_text": lambda x: x["text"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "format_notes": lambda x: x["format_notes"],
            "character_notes": lambda x: x["character_notes"],
            "web_notes": lambda x: x["web_notes"]
        }) | summarize_prompt | model
    )

    result = summarize_chain.invoke({
        "text": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "format_notes": format_notes,
        "character_notes": character_notes,
        "web_notes": web_notes
    })

    return result.content

def determine_tone(model: ChatOpenAI, input_lang: str, output_lang: str, transcript: str,
                   format_description: str = None, web_context: str = None):
    prompt_str = """
    # Role: {input_lang} Tone and Style Analyzer
    
    ## Input
    
    ### Web Context
    
    {web_notes}
    
    ### Transcript

    {scene_text}
    
    ### Format Description
    
    {format_notes}

    ## Instructions

    You are assisting a translator by analyzing the overall **tone and speech level** of the following scene.  
    Your analysis should help guide translation choices in {output_lang} — especially around formality, emotional undercurrents, and delivery style.

    Focus on:
    - Overall tone (e.g., casual, serious, comedic, emotional, subdued)
    - Notable speech patterns (e.g., blunt, polite, indirect, teasing)
    - Formality level or shifts in speech style
    - Any emotional or interpersonal cues that are directly observable

    Do **not** translate the lines or interpret underlying emotion beyond what is evident.

    ## Output Format

    Write **1 to 2 concise sentences** describing the tone and delivery style.  
    Focus on what would be **most helpful for a translator** to know when rendering speech into {output_lang}.
    """

    format_notes = (
        f"The following format description may help you understand how the scene is structured:\n{format_description}"
        if format_description else "No format description was provided."
    )
    web_notes = f"You may also consider the following series background:\n{web_context}" if web_context else "No web context was provided."

    prompt = ChatPromptTemplate.from_template(prompt_str)

    tone_chain = (
        RunnableMap({
            "scene_text": lambda x: x["transcript"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "format_notes": lambda x: x["format_notes"],
            "web_notes": lambda x: x["web_notes"]
        }) | prompt | model
    )

    result = tone_chain.invoke({
        "transcript": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "format_notes": format_notes,
        "web_notes": web_notes
    })

    return result.content


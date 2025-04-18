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
                            series_name: str, keywords: str, transcript: str):
    
    info_need_prompt_str = """
    # Role: Translation Context Analyst

    ## Instruction

    You are helping a translator identify what **external background information** would support accurate translation of a Japanese drama scene.

    Focus specifically on the following two types of background information:

    1. **Character relationships** — if multiple characters are mentioned, determine whether their roles or relationships are unclear and would benefit from clarification.

    2. **Story premise or genre** — identify whether the overall setting, premise, or narrative style is unclear (e.g., slice of life, romance, supernatural, mystery, etc.) and whether that context would help guide tone or phrasing choices.
    ## Transcript

    {transcript}

    ## Output

    Write exactly two bullet points:
    - One about **character relationships**
    - One about the **story premise or genre**

    Use clear, natural {output_lang}.
    """
    
    info_needed_prompt = ChatPromptTemplate.from_template(info_need_prompt_str)
    
    query_generation_prompt_str = """
    # Role: Internet Search Query Writer

    ## Instruction

    You are writing a web search query to help a translator find background information about a Japanese series.  
    The goal is to retrieve information that matches the described research need below.

    ## Input

    Series Title: {series_name}  
    User Keywords: {keywords}  
    Research Need: {info_need}

    ## Output

    Write **one clean web search query** in natural {output_lang}.  
    It should look like a normal Google search — simple, lowercase if applicable, and no extra formatting.
    Only return the query string.
    """    

    query_generator_prompt = ChatPromptTemplate.from_template(query_generation_prompt_str)
    
    web_context_prompt_str = """
    # Role: Translator Support Assistant

    ## Instructions

    You are assisting a translator working on a project involving the series titled **{series_name}**.

    Use the search results below to construct a helpful, factual background summary in natural {output_lang}.  
    Only use information that is clearly supported by the search results.  
    Do **not** speculate, interpret tone, or invent any missing details.

    ### Focus Areas

    You are specifically looking for the following two types of information:
    - **Character relationships** — e.g., names, roles, group dynamics, or how characters relate to each other.
    - **Story premise and genre** — e.g., setting, type of narrative, and what kind of story this is.

    If no information is available for a category, briefly acknowledge it.

    ### Important Guidelines

    - Do **not** include personal opinions, guesses, or unverified claims.
    - Keep the tone neutral and factual.
    - Do not fabricate names, backstories, or settings not explicitly mentioned in the search results.

    ### Search Results

    {search_results}

    ## Output Format

    Write a clearly formatted summary in natural {output_lang} using **bolded section labels** followed by a colon.  
    Each labeled section (e.g., **Character Relationships:**) should be on its own line.  
    Write **no more than 2–4 sections total**, each limited to **1–2 concise sentences**.  
    Do **not** use bullet points or numbered lists.
    """

    web_context_prompt = ChatPromptTemplate.from_template(web_context_prompt_str)
    
    # Final single chain
    web_context_chain = (
        RunnableMap({
            "series_name": lambda x: x["series_name"],
            "keywords": lambda x: x["keywords"],
            "transcript": lambda x: x["transcript"],
            "output_lang": lambda x: x["output_lang"]
        })
        # Step 1: Extract info need
        | RunnableMap({
            "info_need": info_needed_prompt | model,
            "series_name": lambda x: x["series_name"],
            "keywords": lambda x: x["keywords"],
            "output_lang": lambda x: x["output_lang"]
        })
        # Step 2: Generate query
        | RunnableMap({
            "query_result": query_generator_prompt | model,
            "series_name": lambda x: x["series_name"],
            "output_lang": lambda x: x["output_lang"]
        })
        # Step 3: Search the web
        | RunnableMap({
            "search_results": lambda x: search_tool.invoke({"query": x["query_result"].content}),
            "series_name": lambda x: x["series_name"],
            "output_lang": lambda x: x["output_lang"]
        })
        # Step 4: Format the web context summary
        | web_context_prompt
        | model
    )
    
    result = web_context_chain.invoke({
        "series_name": series_name,
        "keywords": keywords,
        "transcript": transcript,
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

    ### Format Description

    {format_notes}

    ### Characters

    {character_notes}

    ### Transcript

    {scene_text}

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

    ## Output Format

    Write one concise paragraph in natural {output_lang} that clearly summarizes the events and developments of this scene.
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


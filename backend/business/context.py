from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_tavily import TavilySearch


def generate_web_query(model: ChatOpenAI, series_name: str, key_words: str, 
                       input_lang="ja", output_lang: str = "en") -> str:
    """
    Generate a natural language search query using free-form user keywords and the series title.

    Returns:
        A single search query string in the output language.
    """

    prompt_str = """
    # Role: Search Prompt Generator for Translators

    ## Task

    You are helping a translator gather background information about a fictional work titled "{series_name}" in {input_lang}.  
    Using the user-provided keywords below, generate **one natural language search query** (in {output_lang}) that could be used to retrieve useful character or context information.

    The query should:
    - Use the keywords "{keywords}" and the title "{series_name}".
    - Phrase the query naturally, as if typed into a search engine.
    - Do not add assumptions or filler like "tell me about".
    - The goal is to help a translator get concise and relevant results.

    ## Keywords

    {keywords}

    ## Output Format

    One natural language search query in {output_lang}.
    """

    prompt = ChatPromptTemplate.from_template(prompt_str)

    chain = (
        RunnableMap({
            "series_name": lambda x: x["series_name"],
            "keywords": lambda x: x["keywords"],
            "output_lang": lambda x: x["output_lang"],
            "input_lang": lambda x: x["input_lang"]
        }) | prompt | model
    )

    result = chain.invoke({
        "series_name": series_name,
        "keywords": key_words,
        "output_lang": output_lang,
        "input_lang": input_lang
    })

    return result.content.strip()


def generate_web_context(model: ChatOpenAI, search_tool: TavilySearch,
                         input_lang: str, output_lang: str,
                         series_name: str, keywords: str):
    """
    Generate a general-purpose web context summary using a natural-language search query.

    Returns:
        A string summary of relevant background information based on the provided series name and keywords.
    """
    # Step 1: Generate a search query from the keywords
    query = generate_web_query(
        model=model,
        key_words=keywords,
        series_name=series_name,
        input_lang=input_lang,
        output_lang=output_lang
    )

    # Step 2: Run the query
    search_results = search_tool.invoke({"query": query})

    # Step 3: Ask GPT to summarize the results for translation purposes
    summary_prompt = ChatPromptTemplate.from_template("""
    # Role: Translator Support Assistant

    ## Task

    You are helping a translator understand key background information about the fictional work "{series_name}".  
    Using the search results and user-provided keywords, write a concise and readable summary.

    ## Input

    - Title: {series_name}
    - Keywords: {keywords}
    - Search Results: {search_results}

    ## Instructions

    - Write 1–3 short paragraphs (maximum) summarizing:
    - Important characters and their relationships
    
    ## Output Format

    A few concise paragraphs in {output_lang}.
    """)

    summary_chain = (
        RunnableMap({
            "series_name": lambda x: x["series_name"],
            "keywords": lambda x: x["keywords"],
            "search_results": lambda x: x["search_results"],
            "output_lang": lambda x: x["output_lang"]
        }) | summary_prompt | model
    )

    result = summary_chain.invoke({
        "series_name": series_name,
        "keywords": keywords,
        "search_results": search_results,
        "output_lang": output_lang
    })

    return result.content.strip()


def generate_character_list(model: ChatOpenAI, 
                            input_lang: str, output_lang: str, 
                            transcript: str, context: Optional[dict] = None):
    """
    Generate a character list from a transcript.
    
    Args:
        model: ChatOpenAI model
        input_lang: Input language code
        output_lang: Output language code
        transcript: The dialogue transcript
        context: Optional dictionary with context data (e.g., {"web_context": "...", "summary": "..."})
    """
    context = context or {}
    
    # Build context section dynamically from all context keys
    context_sections = []
    for key, value in context.items():
        if value:
            # Format key as title (e.g., "web_context" -> "Web Context")
            title = key.replace('_', ' ').title()
            context_sections.append(f"### {title}\n\n{value}")
    
    context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."
    
    prompt_str = """
    # Role: {input_lang} Character Identifier

    ## Input

    {context_text}

    ### Transcript

    {transcript}

    ## Instructions

    You are assisting a translator by identifying characters in a scene that is in {input_lang}.
    Use the dialogue transcript and any provided context to extract characters in {output_lang}.

    For each character include:
    - **Name** — the most complete form you can find
    - **Very High-Level Summary** — one short clause capturing their role / personality / tone
    - If one character is **clearly the narrative focus** (appears most, drives the scene), add **[Narrative Focus]**

    Rely only on evidence from the transcript or context — do **not** speculate.

    ## Output Format

    All output must be in {output_lang}.

    - When the web context supplies a fuller name (e.g., “Sumika Shiun”), use that.
    - If the same person appears under multiple names or forms (e.g., “清夏ちゃん” and “Sumika Shiun”),
    **merge them into one entry** using the full name and list the alias in parentheses.

    Example:  
    - **Sumika Shiun** (also referred to as "清夏ちゃん"): Cheerful classmate who motivates others. [Narrative Focus]

    - For unnamed or minor speakers (e.g., “Student A”), use translated role names in {output_lang}.

    Return **one line per character** in this exact pattern (no nested bullets):

    - **[Character Name]**: [very high-level summary]. [Narrative Focus] (if applicable)
    """

    final_prompt = ChatPromptTemplate.from_template(prompt_str)

    character_chain = (
        RunnableMap({
            "transcript": lambda x: x["transcript"],
            "context_text": lambda x: x["context_text"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en")
        }) | final_prompt | model
    )

    result = character_chain.invoke({
        "transcript": transcript,
        "context_text": context_text,
        "input_lang": input_lang,
        "output_lang": output_lang
    })

    return result.content


def generate_high_level_summary(model: ChatOpenAI, 
                                input_lang: str, output_lang: str, 
                                transcript: str, context: Optional[dict] = None):
    """
    Generate a high-level summary from a transcript.
    
    Args:
        model: ChatOpenAI model
        input_lang: Input language code
        output_lang: Output language code
        transcript: The dialogue transcript
        context: Optional dictionary with context data (e.g., {"character_list": "...", "web_context": "..."})
    """
    context = context or {}
    
    # Build context section dynamically from all context keys
    context_sections = []
    for key, value in context.items():
        if value:
            # Format key as title (e.g., "character_list" -> "Character List")
            title = key.replace('_', ' ').title()
            context_sections.append(f"### {title}\n\n{value}")
    
    context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."
    
    prompt_str = """
    # Role: {input_lang} Scene Summary Assistant

    ## Input

    {context_text}

    ### Transcript

    {transcript}

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

    summarize_prompt = ChatPromptTemplate.from_template(prompt_str)

    summarize_chain = (
        RunnableMap({
            "transcript": lambda x: x["transcript"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "context_text": lambda x: x["context_text"],
        }) | summarize_prompt | model
    )

    result = summarize_chain.invoke({
        "transcript": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "context_text": context_text
    })

    return result.content


def generate_synopsis(model: ChatOpenAI, 
                      input_lang: str, output_lang: str, 
                      transcript: str, context: Optional[dict] = None):
    """
    Generate a synopsis from a transcript.
    
    Args:
        model: ChatOpenAI model
        input_lang: Input language code
        output_lang: Output language code
        transcript: The dialogue transcript
        context: Optional dictionary with context data (e.g., {"character_list": "...", "web_context": "..."})
    """
    context = context or {}
    
    # Build context section dynamically from all context keys
    context_sections = []
    for key, value in context.items():
        if value:
            # Format key as title (e.g., "character_list" -> "Character List")
            title = key.replace('_', ' ').title()
            context_sections.append(f"### {title}\n\n{value}")
    
    context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."
    
    prompt_str = """
    # Role: {input_lang} Synopsis Generator

    ## Input

    {context_text}

    ### Transcript

    {transcript}

    ## Instructions

    You are creating a comprehensive synopsis of this episode or scene in {output_lang}.

    Using the supporting information and the transcript, describe everything that happens:

    - All plot points and story developments in order
    - All character moments and interactions
    - All revelations, decisions, and turning points
    - Scene changes and topic shifts

    Be thorough and complete. Cover all events from the transcript without omitting details.

    ## Output Format

    Write a comprehensive synopsis in natural {output_lang}. Include all events and developments - do not limit length.
    """

    synopsis_prompt = ChatPromptTemplate.from_template(prompt_str)

    synopsis_chain = (
        RunnableMap({
            "transcript": lambda x: x["transcript"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "context_text": lambda x: x["context_text"],
        }) | synopsis_prompt | model
    )

    result = synopsis_chain.invoke({
        "transcript": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "context_text": context_text
    })

    return result.content


def generate_recap(model: ChatOpenAI,
                   input_lang: str, output_lang: str,
                   contexts: list[dict]) -> str:
    """
    Generate a comprehensive recap from multiple prior context dicts.
    
    This creates a "前回のあらすじ" (previously on...) style summary that:
    - Lists all established characters with their personalities/roles
    - Summarizes story progression across all provided contexts
    - Provides enough detail for translation continuity
    
    Args:
        model: ChatOpenAI model
        input_lang: Input language code (language of the original content)
        output_lang: Output language code
        contexts: List of context dicts in chronological order
                  Each dict may contain keys like: character_list, synopsis, summary, web_context
    
    Returns:
        A comprehensive recap string in output_lang
    """
    # Collect all unique keys across all contexts
    all_keys = set()
    for ctx in contexts:
        all_keys.update(ctx.keys())
    
    # Remove metadata keys that shouldn't be included in recap
    metadata_keys = {'seriesName', 'keywords', 'inputLanguage', 'outputLanguage', 'exportDate'}
    all_keys = all_keys - metadata_keys
    
    # Extract values for each key across all contexts
    sections_data = {}
    for key in all_keys:
        values = []
        for i, ctx in enumerate(contexts):
            value = ctx.get(key, "")
            if value and str(value).strip():
                values.append((i, str(value).strip()))
        if values:
            sections_data[key] = values
    
    # If no data provided, return empty string
    if not sections_data:
        return ""
    
    # Build the sections dynamically
    context_sections = []
    for key, values in sections_data.items():
        # Format key as title (e.g., "character_list" -> "Character List")
        title = key.replace('_', ' ').title()
        
        # Combine values from different parts
        combined = "\n\n".join([f"### Part {i+1}\n{val}" for i, val in values])
        context_sections.append(f"## {title}\n\n{combined}")
    
    all_context = "\n\n".join(context_sections)
    
    prompt_str = """
    # Role: Continuity Recap Generator for Translators

    ## Task

    You are helping a translator working with {input_lang} source material by creating a comprehensive "Previously On" style recap from multiple prior scenes.
    The contexts are provided in chronological order.
    This recap will be used as context for translating future content, so it must be thorough enough to:
    - Identify returning characters and recall their personalities/roles
    - Understand ongoing story developments and relationships
    - Maintain consistent tone and terminology

    ## Input Context

    {all_context}

    ## Instructions

    Create a comprehensive recap in {output_lang} that includes all information from the provided contexts:

    1. **All Established Characters**: List every character that has appeared, with their key personality traits, roles, and relationships. Merge duplicate entries.

    2. **All Story Events**: Include all events and developments in chronological order. Do not summarize or condense - include all details.

    3. **All Context Information**: Include tone, setting, and any other information provided.

    **Important**: Be thorough and complete. The translator needs all details to handle returning characters and ongoing plot threads. Include everything from the contexts without omitting details.

    ## Output Format

    Write a comprehensive recap in natural {output_lang}. Organize the information clearly but include all details from the contexts. Do not limit length.
    """

    recap_prompt = ChatPromptTemplate.from_template(prompt_str)
    
    recap_chain = (
        RunnableMap({
            "all_context": lambda x: x["all_context"],
            "input_lang": lambda x: x["input_lang"],
            "output_lang": lambda x: x["output_lang"]
        }) | recap_prompt | model
    )
    
    result = recap_chain.invoke({
        "all_context": all_context,
        "input_lang": input_lang,
        "output_lang": output_lang
    })
    
    return result.content.strip()


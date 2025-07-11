from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableMap
from langchain_community.tools.tavily_search.tool import TavilySearchResults


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


def generate_web_context(model: ChatOpenAI, search_tool: TavilySearchResults,
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
                            transcript: str, web_context: str = None):
    prompt_str = """
    # Role: {input_lang} Character Identifier

    ## Input

    ### Web context

    {web_context}

    ### Transcript

    {transcript}

    ## Instructions

    You are assisting a translator by identifying characters in a scene that is in {input_lang}.
    Use the dialogue transcript (and any web context) to extract characters in {output_lang}.

    For each character include:
    - **Name** — the most complete form you can find
    - **Very High-Level Summary** — one short clause capturing their role / personality / tone
    - If one character is **clearly the narrative focus** (appears most, drives the scene), add **[Narrative Focus]**

    Rely only on evidence from the transcript or web context — do **not** speculate.

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
    
    web_context = f"The following is additional information pulled from the web:\n{web_context}" if web_context else "No additional web context."

    final_prompt = ChatPromptTemplate.from_template(prompt_str)

    character_chain = (
        RunnableMap({
            "transcript": lambda x: x["transcript"],
            "web_context": lambda x: x["web_context"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en")
        }) | final_prompt | model
    )

    result = character_chain.invoke({
        "transcript": transcript,
        "web_context": web_context,
        "input_lang": input_lang,
        "output_lang": output_lang
    })

    return result.content


def generate_high_level_summary(model: ChatOpenAI, 
                                input_lang: str, output_lang: str, 
                                transcript: str, character_list: str = None):
    prompt_str = """
    # Role: {input_lang} Scene Summary Assistant

    ## Input

    ### Characters

    {character_list}

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
    
    # Optional inserts
    character_list = f"The following characters were identified:\n{character_list}" if character_list else "No characters were identified."

    summarize_prompt = ChatPromptTemplate.from_template(prompt_str)

    summarize_chain = (
        RunnableMap({
            "transcript": lambda x: x["transcript"],
            "input_lang": lambda x: x.get("input_lang", "ja"),
            "output_lang": lambda x: x.get("output_lang", "en"),
            "character_list": lambda x: x["character_list"],
        }) | summarize_prompt | model
    )

    result = summarize_chain.invoke({
        "transcript": transcript,
        "input_lang": input_lang,
        "output_lang": output_lang,
        "character_list": character_list
    })

    return result.content


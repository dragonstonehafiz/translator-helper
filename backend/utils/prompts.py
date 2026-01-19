class PromptGenerator:
    def __init__(self):
        pass

    def generate_translate_sub_prompt(
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        target_lang: str = "en"
    ):
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
        If the text contains a speaker label (e.g. "Speaker1: ."), remove the label.
        """.strip()

        return system_prompt

    def generate_character_list_prompt(
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        output_lang: str = "en"
    ):
        context = context or {}
        context_sections = []
        for key, value in context.items():
            if value:
                title = key.replace("_", " ").title()
                context_sections.append(f"### {title}\n\n{value}")

        context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."

        system_prompt = f"""
        # Role: {input_lang} Character Identifier

        ## Instructions

        You are assisting a translator by identifying characters in a scene that is in {input_lang}.
        Use the dialogue transcript and any provided context to extract characters in {output_lang}.

        For each character include:
        - **Name** - the most complete form you can find
        - **Very High-Level Summary** - one short clause capturing their role / personality / tone
        - If one character is **clearly the narrative focus** (appears most, drives the scene), add **[Narrative Focus]**

        Rely only on evidence from the transcript or context - do **not** speculate.

        ## Context

        {context_text}

        ## Output Format

        All output must be in {output_lang}.

        - When the context supplies a fuller name (e.g., "Sumika Shiun"), use that.
        - If the same person appears under multiple names or forms (e.g., “清夏ちゃん” and “紫雲さん”),
        **merge them into one entry** using the full name and list the alias in parentheses.

        Example:  
        - **Sumika Shiun** (also referred to as "清夏ちゃん"): Cheerful classmate who motivates others. [Narrative Focus]

        - For unnamed or minor speakers (e.g., “Student A”), use translated role names in {output_lang}.

        Return **one line per character** in this exact pattern (no nested bullets):

        - **[Character Name]**: [very high-level summary]. [Narrative Focus] (if applicable)
        """.strip()

        return system_prompt

    def generate_summary_prompt(
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        output_lang: str = "en"
    ):
        context = context or {}
        context_sections = []
        for key, value in context.items():
            if value:
                title = key.replace("_", " ").title()
                context_sections.append(f"### {title}\n\n{value}")

        context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."

        system_prompt = f"""
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
        """.strip()

        return system_prompt

    def generate_synopsis_prompt(
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        output_lang: str = "en"
    ):
        context = context or {}
        context_sections = []
        for key, value in context.items():
            if value:
                title = key.replace("_", " ").title()
                context_sections.append(f"### {title}\n\n{value}")

        context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."

        system_prompt = f"""
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
        """.strip()

        return system_prompt

    def generate_recap_prompt(
        self,
        all_context: str,
        input_lang: str = "ja",
        output_lang: str = "en"
    ):
        system_prompt = f"""
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
        """.strip()

        return system_prompt

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
        Do not add any speaker names or labels (e.g. "Producer:").
        """.strip()

        return system_prompt

    def generate_translate_batch_prompt(
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

        You will receive a batch of {input_lang} lines, each formatted as:
        `N. Speaker (Xs): Line`

        Translate **each line** into {target_lang}. Preserve the numbering, speaker label, and time length exactly.
        Only translate the text **after** the first colon.
        Do not add or remove lines. Do not merge or split lines. Each output line must map 1:1 to the corresponding input line number.

        ### IMPORTANT

        You must translate **only** the text inside <LINES> and </LINES>.
        Do not translate or repeat any context or other lines.
        Output the same number of lines in the same order, preserving the numbering.

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
        Preserve explicit line breaks (e.g. "\\N") and any inline formatting tags.

        ### Context

        {context_block}

        ## Output Format

        Output only the translated batch lines in the exact same `N. Speaker: Line` format.
        Do not add headings, labels, or commentary.
        """.strip()

        return system_prompt

    def generate_review_batch_prompt(
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

        You are a professional translation reviewer. Your job is to check existing translations for accuracy and naturalness.

        ## Instructions

        You will receive a batch of lines with both source and translated text, formatted as:
        `N. Speaker (Xs): [SOURCE] => [TRANSLATION]`

        Review each translation and output the corrected translation if needed.
        If the translation is already correct, output it unchanged.

        ### IMPORTANT

        - Preserve numbering, speaker label, and time length exactly.
        - Do not add or remove lines. Do not merge or split lines.
        - The source text is in {input_lang}. The translation must be in {target_lang}.
        - Only modify the translation text after `=>`.
        - Output one line per input line in the same order.

        ### Context

        {context_block}

        ## Output Format

        `N. Speaker (Xs): [TRANSLATION]`
        """.strip()

        return system_prompt

    def generate_batch_plan_prompt(
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        output_lang: str = "en",
    ):
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
        self,
        context: dict | None = None,
        input_lang: str = "ja",
        output_lang: str = "en",
        max_batch_size: int = 50,
        original_reason: str = "",
    ):
        context = context or {}
        context_sections = []
        for key, value in context.items():
            if value:
                title = key.replace("_", " ").title()
                context_sections.append(f"### {title}\n\n{value}")

        context_text = "\n\n".join(context_sections) if context_sections else "No additional context provided."
        original_reason_text = original_reason.strip() or "No original batch reason provided."

        system_prompt = f"""
        # Role

        You are a subtitle batch-splitting assistant for translators working from {input_lang} into {output_lang}.

        ## Task

        You will receive a numbered subtitle span that was already identified as one coherent batch,
        but it is too large and must be split into smaller consecutive batches.

        ## Requirements

        - Every returned batch must stay within the provided subtitle span.
        - Batches can be at most {max_batch_size} lines long.
        - Every batch size must be within the range [1, {max_batch_size}].
        - Preserve the original ordering.
        - Do not create overlapping batches.
        - Do not leave gaps.
        - Cover every subtitle line in the provided span exactly once.
        - Split the span into the smallest number of coherent consecutive batches that satisfy the maximum size.
        - If the span contains one long scene, divide it into multiple consecutive sub-batches at the best natural breakpoints available.
        - Before outputting, verify each batch length using `end_index - start_index + 1`.

        ## Original Batch Reason

        {original_reason_text}

        ## Context

        {context_text}

        ## Output Format

        Return JSON only.
        Do not include markdown fences.
        Do not include commentary.
        Output exactly this shape:

        {{
          "batches": [
            {{"start_index": 261, "end_index": 289, "reason": "First part of the confrontation and defense scene."}},
            {{"start_index": 290, "end_index": 330, "reason": "Resolution of the confrontation and renewed commitment."}}
          ]
        }}
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
        # CRITICAL: Output Language Requirement

        **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

        # Role

        You are a subtitle analysis assistant helping build a character reference list from dialogue in {input_lang}.

        # Task

        From the provided subtitle text, produce a character list in {output_lang}.

        - Identify all characters who speak or are referenced.
        - Merge references that clearly refer to the same person.
        - Do not invent relationships or facts not supported by the text/context.

        # Context

        {context_text}

        # Output format (IMPORTANT)

        Output only the character list. No extra commentary.

        Use this exact structure:

        CHARACTER 1
        Name: ...
        Description: ...
        Role: ...

        CHARACTER 2
        ...

        Rules:
        - Keep one CHARACTER block per person/identity.
        - Keep Description and Role short (1-2 lines each).
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
        # CRITICAL: Output Language Requirement

        **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

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
        **Do NOT write this paragraph in {input_lang}. The entire output MUST be in {output_lang}.**
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
        # CRITICAL: Output Language Requirement

        **You MUST respond ENTIRELY in {output_lang}. Do NOT respond in {input_lang} or any other language. Every single word must be in {output_lang}. This is non-negotiable.**

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
        **Do NOT write this synopsis in {input_lang}. The entire output MUST be in {output_lang}.**
        """.strip()

        return system_prompt

    def generate_recap_prompt(
        self,
        all_context: str,
        input_lang: str = "ja",
        output_lang: str = "en"
    ):
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

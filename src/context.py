def analyze_format(client, text: str, model: str = "gpt-4o-mini", 
                   input_lang: str = "ja", target_lang: str = "en",
                   temperature=0.5, top_p=0.5):
    prompt = f"""
    # Role

    You are an assistant helping translators understand the structural format of a scene based on {input_lang} dialogue.

    # Instructions

    Examine the text and describe the **structure and delivery format** in natural {target_lang}.

    Focus on **how the dialogue is organized**, and whether characters are interacting or delivering isolated lines.

    ### Important:
    - Do **not** assume a conversation simply because multiple speaker names appear.
    - Only classify the scene as interactive *if the characters are clearly responding to each other’s lines*.
    - If each speaker talks independently, without responding to others, treat it as a sequence of monologues.

    ### What to include:
    - Whether the scene consists of monologue, interactive dialogue, narration, or a mix.
    - How many speakers are present (if discernible).
    - Whether speakers are engaging with one another or simply delivering separate reflections.
    - Any structural patterns (e.g., speaker-separated entries, timestamped logs, introspective journaling).

    # Output Format

    Write a short paragraph that objectively describes how the text is structured and delivered. Be literal and grounded in what is observable in the dialogue — not inferred from content.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=400,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content.strip()

def identify_characters(client, text: str, format_description: str = None,
                        model: str = "gpt-4o-mini", input_lang: str = "ja", target_lang: str = "en",
                        temperature=1.0, top_p=1.0):
    
    # If a format description is provided, include it in the prompt.
    if format_description is not None:
        format_string = "Consider the following format when interpreting the structure:\n" + format_description
    else:
        format_string = ""

    character_identification_prompt = f"""
    # Role

    You are a translation assistant specializing in source analysis to support translations from {input_lang} to {target_lang}.
    Your job is to identify characters and key individuals in the scene to support accurate and consistent translation.

    # Instructions

    Analyze the following lines and extract all identifiable characters.
    {format_string}

    For each character:
    - Provide their **name**.
      - If the character speaks using a first-person pronoun (e.g., 俺 or 私), try to resolve their actual name if it appears elsewhere (e.g., if someone addresses them directly).
      - Prefer using proper names. If uncertain, use the pronoun but clearly mark that it was inferred (e.g., “俺 (inferred)”).

    - Note any clearly observable **traits or roles**, such as speaking style (casual, blunt, formal), apparent relationships (e.g., sibling, clubmate), or recurring functions (e.g., narrator, side character).
    
    - If one character is **clearly the narrative focus** — meaning they appear most frequently, drive the events, or are presented as central to the scene — add the label **[Narrative Focus]** at the end of their entry.
      - Only do this if it is unmistakable from the dialogue and speaker balance.
      - Do **not** infer this based solely on the use of first-person pronouns.

    Avoid speculative interpretation or over-inference. Base your output only on what is clearly indicated in the text.

    # Output Format

    Return a list like this:

    - Name: [name or pronoun] — Traits: [brief, factual description]. [Narrative Focus] (if applicable)

    Include only one entry per distinct character.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": character_identification_prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content.strip()

def summarize(client, text: str, format_description: str = None, character_list: str = None,
              model: str = "gpt-4o-mini", input_lang: str = "ja", target_lang: str = "en",
              temperature=1.0, top_p=1.0):
    
    # If a format description is provided, include it in the prompt.
    if format_description is not None:
        format_string = "Consider the following format when interpreting the structure:\n" + format_description
    else:
        format_string = "No format description was created task."
        
    # If a character list is provided, include it in the prompt.
    if character_list is not None:
        character_list = "This is a list of identified character:\n" + character_list
    else:
        character_list = "No characters were identified task."
        

    scene_synopsis_prompt = f"""
    # Role

    You are a translation assistant supporting translations from {input_lang} to {target_lang}.
    Your job is to provide a high-level synopsis that helps translators quickly understand the situation and setting of a scene before working on the dialogue.

    # Instructions

    Based on the following lines, write a brief synopsis in natural {target_lang} that explains the overall premise of the scene.
    Focus on the setting, general situation, and any relevant background or circumstances that help explain the context of the conversation.

    {format_string}
    
    {character_list}

    Avoid retelling the dialogue line by line or describing specific actions. 
    Do not interpret tone, emotional nuance, or character psychology — the goal is to orient the translator, not analyze the scene.

    # Output Format

    Write a short paragraph that captures the essence of the scene: where it takes place, what’s going on, and any relevant background needed to understand the dialogue in context.
    """

    secondary_prompt = f"""
    # Role

    You are a post-processor ensuring that scene synopses derived from {input_lang} content are factual and neutral to support accurate translation into {target_lang}.

    # Instructions

    Review the synopsis and remove or rephrase any parts that speculate on emotions, suggest interpersonal dynamics, or introduce subjective interpretation.
    Avoid phrases like “playful,” “lighthearted,” or references to admiration, teasing, or personality traits — unless these are explicitly stated in the original {input_lang} dialogue.

    Keep the synopsis focused on the setting, situation, and surface-level dialogue topics that are clearly conveyed in the original text.
    Avoid adding tone, narrative style, or implied meaning not directly grounded in the input.

    # Output Format

    Return a brief, objective synopsis written in clear and natural {target_lang}.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": scene_synopsis_prompt},
            {"role": "user", "content": text},
            {"role": "user", "content": secondary_prompt}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content.strip()



def determine_tone(client, text: str, format_description: str = None,
                   model: str = "gpt-4o-mini", input_lang: str = "ja", target_lang: str = "en",
                   temperature=1.0, top_p=1.0):
    
    # If a format description is provided, include it in the prompt.
    if format_description is not None:
        format_string = "Consider the following format when interpreting the structure:\n" + format_description
    else:
        format_string = ""

    tone_analysis_prompt = f"""
    # Role

    You are a translation assistant who specializes in analyzing tone and speech style to support translation from {input_lang} to {target_lang}.
    Your job is to help translators understand the emotional and interpersonal dynamics in a scene before translating.

    # Instructions

    Analyze the tone and speech level of the following lines. 
    Consider emotional shifts, pacing, speaker intent, and speech level (e.g., formal, informal, blunt, indirect). 
    Note any features such as sarcasm, teasing, hierarchy, or emotional restraint, but do not speculate or over-explain.

    {format_string}

    Avoid translating the lines. Focus entirely on analyzing the tone based on linguistic cues and context.

    # Output Format

    Write **1 to 2 short sentences** describing the overall tone and style of speech. 
    Keep it concise and focused on what would directly inform translation choices.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": tone_analysis_prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content.strip()


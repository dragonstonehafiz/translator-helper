def summarize(client, text: str, model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature=1.0, top_p=1.0):
    
    scene_synopsis_prompt = f"""
    # Role

    You are a translation assistant supporting translations from {input_lang} to {target_lang}.
    Your job is to provide a high-level synopsis that helps translators quickly understand the situation and setting of a scene before working on the dialogue.

    # Instructions

    Based on the following lines, write a brief synopsis in natural {target_lang} that explains the overall premise of the scene.
    Focus on the setting, general situation, and any relevant background or circumstances that help explain the context of the conversation.

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
    Do not add any content that goes beyond what is clearly indicated in the original {input_lang} scene.
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

    return response.choices[0].message.content


def identify_characters(client, text: str, model: str = "gpt-4o-mini", 
                        input_lang: str = "ja", target_lang: str = "en",
                        temperature=1.0, top_p=1.0):
    
    character_identification_prompt = f"""
    # Role

    You are a translation assistant specializing in source analysis to support translations from {input_lang} to {target_lang}.
    Your job is to help identify characters and key individuals mentioned in the text to assist with consistent and accurate translation.

    # Instructions

    Analyze the following lines and extract any names or references to identifiable people. 
    If possible, infer their likely role (e.g., friend, boss, sibling) and personality traits (e.g., formal, flirty, shy) based on their language and context.
    Focus on characters who appear multiple times or are clearly significant.

    Avoid guessing wildly — only include individuals who can be reasonably inferred.

    # Output Format

    Return a list in this format:

    - Name: [name] — Traits: [optional guess]

    Only include one entry per character or person.
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

    return response.choices[0].message.content


def identify_glossary_terms(client, text: str, model: str = "gpt-4o-mini", 
                             input_lang: str = "ja", target_lang: str = "en",
                             temperature=1.0, top_p=1.0):

    glossary_extraction_prompt = f"""
    # Role

    You are a translation assistant with expertise in identifying terms in {input_lang} that require consistent or careful translation into {target_lang}.

    # Instructions

    From the following lines, extract only linguistically or culturally significant terms that may need special treatment during translation. Prioritize:

    - Expressions that are repeated or emphasized.
    - Idioms, wordplay, or culturally specific phrases.
    - Honorifics, titles, or speech-level indicators.
    - Uncommon or context-dependent words.

    Do **not** include:
    - Character names unless they contain translatable meaning.
    - Standard or common vocabulary.
    - Phrases where meaning is obvious or trivial in context.

    Avoid speculation about narrative role or symbolism. Keep meanings concise and translation-focused.

    # Output Format

    Return a list in this format:

    - Term: [original term] — Meaning: [brief definition], Notes: [optional translation notes]

    If no such terms are found, respond with: “No glossary terms identified.”
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": glossary_extraction_prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content


def determine_tone(client, text: str, model: str = "gpt-4o-mini", 
                      input_lang: str = "ja", target_lang: str = "en",
                      temperature=1.0, top_p=1.0):

    tone_analysis_prompt = f"""
    # Role

    You are a translation assistant who specializes in analyzing tone and speech style to support translation from {input_lang} to {target_lang}. 
    Your job is to help translators understand the emotional and interpersonal dynamics in a scene before translating.

    # Instructions

    Analyze the tone and speech level of the following lines. 
    Consider emotional shifts, pacing, speaker intent, and speech level (e.g., formal, informal, blunt, indirect). 
    Note any features such as sarcasm, teasing, hierarchy, or emotional restraint, but do not speculate or over-explain.

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

    return response.choices[0].message.content



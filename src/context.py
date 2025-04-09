import pysubs2

def summarize(client, text: str, model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature=1.0, top_p=1.0):
    
    scene_summary_prompt = f"""
    # Role

    You are a translation assistant specializing in supporting translations from {input_lang} to {target_lang}.
    Your job is to help translators understand the literal context and sequence of events in a segment before translating.

    # Instructions

    Given a set of lines, write a concise summary in natural {target_lang} that describes the observable actions, events, and dialogue content.
    Do not interpret tone, emotional intent, relationships, or character dynamics. Avoid subjective language, narrative phrasing, or inferred motivations.

    Focus strictly on what is said and done — who speaks, what is mentioned, and any concrete situational developments. Treat the input as a script, not a story.

    Do not translate the lines directly. Provide only a neutral, factual summary of the content.

    # Output Format

    Write a short paragraph summarizing the scene’s events. Include key dialogue topics and actions. Do not include emotional interpretation, speculation, or character analysis.
    """
    
    secondary_prompt = """
    # Role

    You are a scene summarizer focused on factual reporting to support translation tasks.

    # Instructions

    Summarize only what is explicitly stated or shown in the lines: actions, setting details, and topics of dialogue.
    Avoid interpreting emotions, inferring relationships, or using narrative or subjective language.
    Do not describe mood, tone, or themes. Do not include phrases such as “playfully,” “awkward,” “teasing,” “lighthearted,” etc.

    If the content naturally divides into separate parts (e.g. location change, topic change, new speaker focus), break the summary into multiple short paragraphs for clarity.

    # Output Format

    Write a neutral, objective summary using clear and concise language.
    Keep it as brief as possible and convey only essintial information.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": scene_summary_prompt},
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

    - Name: [name] — Role: [optional guess], Traits: [optional guess]

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



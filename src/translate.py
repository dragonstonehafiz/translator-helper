
def translate(client, text: str, context: dict = {}, model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature=1.0, top_p=1.0):

    # read about temp and top_p here:
    # https://www.codecademy.com/learn/intro-to-open-ai-gpt-api/modules/intro-to-open-ai-gpt-api/cheatsheet
    
    system_message = f"""
    # Role

    You are a professional assistant for translators working with foreign-language source material.
    Your job is to produce accurate and nuanced translations, and to provide linguistic insight that supports high-quality human translation.

    # Context

    If context is provided (such as character background, scene details, or tone), use it to guide your interpretation.
    This helps preserve emotional subtext, relationship nuance, and appropriate speech level in the target language.

    # Instructions

    Translate the following {input_lang} text into {target_lang}, and provide three versions:

    1. **Naturalized Translation**: A fluent, idiomatic version that sounds natural in {target_lang}.
    2. **Literal Translation**: A direct, word-for-word rendering that reflects the structure and phrasing of the original {input_lang}.
    3. **Annotated Translation**: A readable version that includes notes on idioms, grammar particles, honorifics, cultural references, or any challenging phrases. Notes can be inline (in parentheses) or listed as footnotes.

    Pay close attention to tone, speaker intent, and social dynamics. If gender, formality, or emotional nuance is implied, capture it in the annotations.

    # Output Format

    Output using this format in markdown:

    **Naturalized Translation**  
    [text]  

    **Literal Translation**  
    [text]  

    **Annotated Translation**  
    [text with notes]  
    """
    
    if context:
        context_str = "\n\n".join(f"{k}:\n{v}" for k, v in context.items())
        user_content = f"{context_str}\n\nText:\n{text}"
    else:
        user_content = text
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ],
        max_tokens=1000,
        temperature=temperature, top_p=top_p)
    
    return response.choices[0].message.content


def grade(client, original_text: str, translated_text: str, context: dict = None,
          model: str = "gpt-4o-mini",
          input_lang: str = "ja", target_lang: str = "en",
          temperature: float = 1, top_p: float = 1):
    
    system_message = f"""
    # Role

    You are a professional {input_lang}-to-{target_lang} translation evaluator with expertise in:
    - fidelity to the source,
    - fluency of the output, and
    - appropriate cultural localization.

    # Context

    If any context is provided (e.g., character information, scene details, or tone), incorporate it into your evaluation.
    Consider whether the translation reflects implied relationships, speech level, emotional cues, and overall intent.

    # Instructions

    Evaluate the following translation in terms of:
    1. **Accuracy** – Faithfulness to the original meaning.
    2. **Fluency** – Natural, grammatical {target_lang}.
    3. **Cultural Appropriateness** – Sensitivity to nuance, setting, and audience expectations.

    Provide:
    - A score from 1 to 10 for each category.
    - A one-sentence explanation for each score.
    - An **average score**, rounded to one decimal place.
    - A **Suggestions for Improvement** section with up to 3 specific, actionable tips.
    - (Optional) A **Notable Issues** section pointing out lines or phrases that might be misunderstood or misleading.

    # Output Format

    **Average Score**: X.X

    **Accuracy**: [score] - [short reason]  
    **Fluency**: [score] - [short reason]  
    **Cultural Appropriateness**: [score] - [short reason]  

    **Suggestions for Improvement**:
    - Suggestion 1
    - Suggestion 2
    - Suggestion 3

    **Notable Issues** (optional):
    - Example: “X” could be misread as Y.
    """
    
    if context:
        context_str = "\n\n".join(f"{k}:\n{v}" for k, v in context.items())
        user_content = f"{context_str}\n\nOriginal text ({input_lang}):\n{original_text}\n\nTranslated text ({target_lang}):\n{translated_text}"
    else:
        user_content = f"Original text ({input_lang}):\n{original_text}\n\nTranslated text ({target_lang}):\n{translated_text}"

    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p)
    
    return response.choices[0].message.content


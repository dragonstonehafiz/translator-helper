import openai

def translate(client, text: str, context: dict = {}, model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature=1.0, top_p=1.0):

    # read about temp and top_p here:
    # https://www.codecademy.com/learn/intro-to-open-ai-gpt-api/modules/intro-to-open-ai-gpt-api/cheatsheet
    
    system_message = f"""
    # Role

    You are a professional assistant for translators working on Japanese Drama CDs.
    Your job is to provide helpful translations and linguistic insight to help the human translator do their job effectively.

    # Context

    If context is provided (such as character traits, scene backstory, or tone), use it to guide the interpretation and translation. 
    The context is meant to help preserve emotional subtext, relationship nuance, and speech level.

    # Instructions

    Translate the following {input_lang} text into {target_lang}, and provide three versions:

    1. **Naturalized Translation**: A fluent {target_lang} version that sounds natural and idiomatic.
    2. **Literal Translation**: A close word-for-word rendering to show original structure and phrasing.
    3. **Annotated Translation**: A readable translation that includes notes on difficult phrases, particles, idioms, or honorifics. Notes can be inline in parentheses or as footnotes.

    Focus on tone, emotional subtext, and speaker intent. If gender, status, or relationships are implied, mention that in the annotations.

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
    - fidelity to source,
    - fluency of the output, and
    - appropriate cultural localization.

    # Context

    If any context is provided (e.g. characters, scene, or tone), incorporate it into your evaluation.
    Check whether the translation reflects character relationships, speech level, and emotional cues accurately.

    # Instructions

    Evaluate the following translation in terms of:
    1. **Accuracy** – Faithfulness to original meaning.
    2. **Fluency** – Natural, grammatical {target_lang}.
    3. **Cultural Appropriateness** – Sensitivity to nuance and adaptation.

    Provide:
    - A score from 1–10 for each category.
    - A one-sentence explanation for each score.
    - An **average score**, rounded to one decimal.
    - A **Suggestions for Improvement** section with up to 3 specific tips.
    - (Optional) List specific lines or phrases that may be misinterpreted.

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


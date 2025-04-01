import openai

def translate(client: openai.OpenAI, text:str, 
              model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature = 1.0, top_p = 1.0):
    # read about temp and top_p here:
    # https://www.codecademy.com/learn/intro-to-open-ai-gpt-api/modules/intro-to-open-ai-gpt-api/cheatsheet
    
    system_message = f"""
    # Role

    You are a professional assistant for translators working on Japanese Drama CDs.
    Your job is to provide helpful translations and linguistic insight to help the human translator do their job effectively.

    # Instructions

    Translate the following Japanese text into English, and provide three versions:

    1. **Naturalized Translation**: A fluent English version that sounds natural and idiomatic.
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
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ],
        max_tokens=500,
        temperature=temperature, top_p=top_p)
    
    return response.choices[0].message.content


def grade(client: openai.OpenAI, original_text: str, translated_text: str,#
          model: str = "gpt-4o-mini",
          input_lang: str = "ja", target_lang: str = "en",
          temperature: float = 1, top_p: float = 1):
    system_message = f"""
    # Role

    You are a professional Japanese-to-English translation evaluator with expertise in:
    - fidelity to source,
    - fluency of the output, and
    - appropriate cultural localization.

    # Instructions

    Evaluate the following translation in terms of:
    1. **Accuracy** – Faithfulness to original meaning.
    2. **Fluency** – Natural, grammatical English.
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
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Original text ({input_lang}):\n{original_text}\n\nTranslated text ({target_lang}):\n{translated_text}"}
        ],
        max_tokens=500,
        temperature=temperature,
        top_p=top_p)
    
    return response.choices[0].message.content


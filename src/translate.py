import openai

def create_client(api_key: str = None):
    if api_key is None:
        api_key = input("Please enter your API key:")
    client = openai.OpenAI(api_key=api_key)
    return client

def translate(client: openai.OpenAI, text:str, 
              model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en",
              temperature = 1.0, top_p = 1.0):
    # read about temp and top_p here:
    # https://www.codecademy.com/learn/intro-to-open-ai-gpt-api/modules/intro-to-open-ai-gpt-api/cheatsheet
    
    system_message = f"""
    # Role
    
    You are a professional translator with expertise in translating dialogue across multiple languages. 
    You understand nuances, context, and tone, ensuring that translations are both accurate and natural. 
    Your primary focus is translating dialogue in a way that preserves the intent, emotion, and cultural relevance of the original text.
    
    # Instructions
    
    - Translate the given text from {input_lang} to {target_lang}.
    - Use natural expressions in {target_lang} while ensuring fidelity to the original meaning.
    - Adapt cultural references only when necessary to improve comprehension.
    - If the dialogue contains slang, idioms, or jokes, translate them in a way that makes sense in {target_lang}.
    - You must include three translations, one which is casual, another respectful, and the third a direct translation of the original line.
    
    # Output Format
    
    - Your output must be purely markdown.
    - It must include the translation and an explanation that is only two sentences long.
    - The translation must only be in {target_lang}.
    
    # Example Output
    Casual Translation
    - TRANSLATED SENTENCE
    - EXPLANATION
        
    Respectful Translation
    - TRANSLATED SENTENCE
    - EXPLANATION
        
    Direct Translation
    - TRANSLATED SENTENCE
    - EXPLANATION
    
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
    
    You are a professional translator and language evaluator with expertise in translation accuracy, fluency, and cultural adaptation. 
    Your task is to evaluate a given translation based on:
    
    1. **Accuracy**: How well the translated text preserves the meaning of the original text.
    2. **Fluency**: Whether the translation is natural and grammatically correct in {target_lang}.
    3. **Cultural Appropriateness**: If necessary, whether adaptations to cultural references were appropriately handled.
    
    # Instructions
    
    - Read the original text in {input_lang} and compare it with the provided translation in {target_lang}.
    - Grade the translation on a scale of 1 to 10 based on the above criteria.
    - Provide a single sentence explanation for each score.
    - Calculate and display the average score.
    
    # Output Format
    
    - Provide three individual scores (Accuracy, Fluency, Cultural Appropriateness) each with a one-sentence explanation.
    - Calculate and display the average score.
    - The output should be written in markdown.
    
    # Example Output
    
    **Average Score**: [average score]
    
    **Accuracy**: [score] - [one sentence explanation]
    
    **Fluency**: [score] - [one sentence explanation]
    
    **Cultural Appropriateness**: [score] - [one sentence explanation]
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


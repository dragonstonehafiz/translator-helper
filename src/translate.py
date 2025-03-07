import openai

def create_client():
    api_key = input("Please enter your API key:")
    client = openai.OpenAI(api_key=api_key)
    return client

def translate(client: openai.OpenAI, text:str, 
              model: str = "gpt-4o-mini", 
              input_lang: str = "ja", target_lang: str = "en"):
    
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
    - Do not add explanations—only return the translated text.
    
    # Output Format
    
    - Return only the translated text in {target_lang} without any additional information.
    - Provide multiple lines (at most 5) that represent different interpretations. Each line should be seperated by a newline.
    - The output should ONLY be in the {target_lang}
    
    DO NOT INCLUDE ANY EXTRA INFORMATION OR EXPLANATION.
    """
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ],
        max_tokens=500)
    
    return response.choices[0].message.content


def grade(client: openai.OpenAI, original_text: str, translated_text: str,
          model: str = "gpt-4o-mini",
          input_lang: str = "ja", target_lang: str = "en"):
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
    - The response should be structured as follows:
    
    Accuracy: [score] - [one sentence explanation]
    Fluency: [score] - [one sentence explanation]
    Cultural Appropriateness: [score] - [one sentence explanation]
    
    Average Score: [average score]
    
    """
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Original text ({input_lang}):\n{original_text}\n\nTranslated text ({target_lang}):\n{translated_text}"}
        ],
        max_tokens=500)
    
    return response.choices[0].message.content


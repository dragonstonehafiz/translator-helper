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
import openai

def validate_openai_api_key(api_key: str) -> bool:
    try:
        client = openai.OpenAI(api_key=api_key)
        _ = client.models.list()  # lightweight test call
        return True
    except Exception:
        return False


import requests

def validate_tavily_api_key(api_key: str) -> bool:
    try:
        resp = requests.get(
            "https://api.tavily.com/search",
            params={"query": "test"},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return resp.status_code == 200
    except Exception:
        return False

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
        resp = requests.post(
            "https://api.tavily.com/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"query": "test"},
            timeout=10,
        )
        if resp.status_code in (401, 403):
            return False
        if not resp.ok:
            return False
        try:
            payload = resp.json()
        except ValueError:
            return False
        if isinstance(payload, dict) and payload.get("error"):
            return False
        return True
    except Exception:
        return False

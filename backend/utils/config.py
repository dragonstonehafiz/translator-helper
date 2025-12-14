import json

DEFAULT_CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "input_lang": "ja",
    "output_lang": "en",
    "whisper_model": "medium",
    "openai_model": "gpt-4o",
    "openai_api_key": "",
    "tavily_api_key": "",
    "temperature": 0.7,
}


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load configuration from a JSON file, or create it with defaults if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Create the file with default config
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict, path: str = DEFAULT_CONFIG_PATH):
    """Save a configuration dictionary to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

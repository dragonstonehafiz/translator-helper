import json
import os
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("translator-helper")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "search_tavily.json")


class SearchTavily:
    def __init__(self):
        self._api_key = ""
        self._status = "not_loaded"
        self._client = None

        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._api_key = cfg.get("api_key", "")
        else:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"api_key": ""}, f, indent=2)

    def configure(self, settings: dict) -> None:
        if not settings:
            return
        if "api_key" in settings:
            self._api_key = settings["api_key"]
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": self._api_key}, f, indent=2)

    def initialize(self) -> None:
        try:
            from tavily import TavilyClient
            if not self._api_key:
                raise ValueError("Tavily API key is required.")
            self._client = TavilyClient(api_key=self._api_key)
            self._client.search("test", max_results=1)
            self._status = "loaded"
            logger.info("Tavily search client loaded")
        except Exception as exc:
            self._status = "error"
            logger.error("Tavily load failed: %s", exc, exc_info=True)
            raise

    def search(self, query: str, max_results: int = 5) -> list[str]:
        if self._client is None:
            raise RuntimeError("Tavily client not initialized.")
        results = self._client.search(query, max_results=max_results)
        snippets = []
        for r in results.get("results", []):
            content = r.get("content", "").strip()
            if content:
                snippets.append(content)
        return snippets

    def get_status(self) -> str:
        return self._status

    def get_settings_schema(self) -> dict:
        return {
            "provider": "search_tavily",
            "title": "Tavily Web Search",
            "fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "password",
                    "placeholder": "tvly-...",
                    "required": True,
                }
            ],
        }

    def get_server_variables(self) -> list[dict]:
        return [{"key": "tavily_status", "label": "Status", "value": self._status}]

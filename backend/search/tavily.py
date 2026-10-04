from dataclasses import dataclass
from typing import ClassVar

from models.config import ConfigField, ModelConfig, TextOption, setting
from models.state import ModelState


@dataclass
class TavilyConfig(ModelConfig):
    """Settings for the Tavily web search provider, saved to search_tavily.json."""

    CONFIG_FILE: ClassVar[str] = "search_tavily.json"
    PROVIDER: ClassVar[str] = "search_tavily"
    TITLE: ClassVar[str] = "Tavily Web Search"

    api_key: ConfigField[str] = setting("API Key", TextOption(password=True, placeholder="tvly-..."), "", required=True)


class SearchTavily:
    """Tavily web search client used by the library update chain to gather reference information for unknown terms."""

    def __init__(self):
        """Load the saved Tavily settings; the client starts NOT_LOADED."""
        self._config = TavilyConfig.load()
        self._state = ModelState.NOT_LOADED
        self._client = None
        self._in_use = False

    @property
    def provider_id(self) -> str:
        """Return the provider identifier declared by the config class."""
        return self._config.PROVIDER

    @property
    def config(self) -> TavilyConfig:
        """Return the current settings."""
        return self._config

    @property
    def state(self) -> ModelState:
        """Return whether the client is initialized."""
        return self._state

    @property
    def in_use(self) -> bool:
        """Return True while a search is running."""
        return self._in_use

    def configure(self, config: TavilyConfig) -> None:
        """Replace the settings; they take effect on the next initialize()."""
        self._config = config

    def initialize(self) -> None:
        """Build the client and validate the API key with a test search."""
        try:
            from tavily import TavilyClient
            if not self._config.api_key.value:
                raise ValueError("Tavily API key is required.")
            self._client = TavilyClient(api_key=self._config.api_key.value)
            self._client.search("test", max_results=1)
            self._state = ModelState.LOADED
        except Exception:
            self._client = None
            self._state = ModelState.ERROR
            raise

    def shutdown(self) -> None:
        """Release the client."""
        self._client = None
        self._state = ModelState.NOT_LOADED

    def search(self, query: str, max_results: int = 5) -> list[str]:
        """Run a Tavily web search and return a list of result content snippets, marking the client in use until it returns."""
        if self._client is None:
            raise RuntimeError("Tavily client is not initialized.")
        self._in_use = True
        try:
            results = self._client.search(query, max_results=max_results)
        finally:
            self._in_use = False
        snippets = []
        for r in results.get("results", []):
            content = r.get("content", "").strip()
            if content:
                snippets.append(content)
        return snippets

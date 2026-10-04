import threading
from collections.abc import Callable, Mapping
from typing import Any, Optional

from audio.interface import AudioModelInterface
from audio.whisperx import AudioWhisperX
# from audio.whisper import AudioWhisper
# from llm.chatgpt import LLMChatGPT
# from llm.claude import LLMClaude
from llm.deepseek import LLMDeepSeek
from llm.interface import LLMInterface
# from llm.llamacpp import LLMLlamaCpp
from models.state import ModelState
from search.tavily import SearchTavily
from utils.logger import setup_logger

logger = setup_logger("translator-helper")

# Provider class per slot; swap in another implementation of the same interface to change providers.
LLM_PROVIDER: Callable[[], LLMInterface] = LLMDeepSeek
AUDIO_PROVIDER: Callable[[], AudioModelInterface] = AudioWhisperX
SEARCH_PROVIDER: Callable[[], SearchTavily] = SearchTavily

LABELS = {"llm": "LLM", "audio": "Audio model", "search": "Search model"}


class ModelManager:
    """Singleton that owns the LLM, audio and search clients: creates and loads them, and tracks which are loading or in use."""

    _instance: Optional["ModelManager"] = None

    def __init__(self):
        """Initialize empty client slots and flags; use get_instance() instead."""
        if ModelManager._instance is not None:
            raise RuntimeError("ModelManager: Please use get_instance()")

        self._lock = threading.Lock()
        self._closed = False
        self._llm_client: Optional[LLMInterface] = None
        self._audio_client: Optional[AudioModelInterface] = None
        self._search_client: Optional[SearchTavily] = None
        self.loading_llm_model = False
        self.loading_audio_model = False
        self.loading_search_model = False
        self.llm_loading_error: Optional[str] = None
        self.audio_loading_error: Optional[str] = None
        self.search_loading_error: Optional[str] = None

    @staticmethod
    def get_instance() -> "ModelManager":
        """Return the singleton ModelManager, creating it on first call."""
        if ModelManager._instance is None:
            ModelManager._instance = ModelManager()
        return ModelManager._instance

    # ── Client access ──────────────────────────────────────────────────────────

    def get_llm_client(self) -> Optional[LLMInterface]:
        """Return the LLM client, or None if it has not been created."""
        return self._llm_client

    def get_audio_client(self) -> Optional[AudioModelInterface]:
        """Return the audio client, or None if it has not been created."""
        return self._audio_client

    def get_search_client(self) -> Optional[SearchTavily]:
        """Return the search client, or None if it has not been created."""
        return self._search_client

    def is_llm_ready(self) -> bool:
        """Return True if the LLM client exists and is LOADED."""
        return self._is_ready("llm")

    def is_audio_ready(self) -> bool:
        """Return True if the audio client exists and is LOADED."""
        return self._is_ready("audio")

    def is_search_ready(self) -> bool:
        """Return True if the search client exists and is LOADED."""
        return self._is_ready("search")

    # ── Use tracking ───────────────────────────────────────────────────────────

    @property
    def llm_in_use(self) -> bool:
        """Return True while the LLM is running a request."""
        return self._in_use("llm")

    @property
    def audio_in_use(self) -> bool:
        """Return True while the audio model is transcribing."""
        return self._in_use("audio")

    @property
    def search_in_use(self) -> bool:
        """Return True while web search is running a query."""
        return self._in_use("search")

    # ── Loading ────────────────────────────────────────────────────────────────

    def load_llm_model(self, settings: Mapping[str, Any] | None = None) -> None:
        """Apply and save submitted settings, then initialize the LLM; raises on rejection or failure."""
        self._load("llm", LLM_PROVIDER, settings)

    def load_audio_model(self, settings: Mapping[str, Any] | None = None) -> None:
        """Apply and save submitted settings, then initialize the audio model; raises on rejection or failure."""
        self._load("audio", AUDIO_PROVIDER, settings)

    def load_search_model(self, settings: Mapping[str, Any] | None = None) -> None:
        """Apply and save submitted settings, then initialize web search; raises on rejection or failure."""
        self._load("search", SEARCH_PROVIDER, settings)

    def shutdown(self) -> None:
        """Refuse further loads and use, then release every created client; one failing client does not stop the others."""
        with self._lock:
            self._closed = True
        for kind in LABELS:
            client = getattr(self, f"_{kind}_client")
            if client is None:
                continue
            try:
                client.shutdown()
            except Exception as exc:
                logger.error("%s shutdown failed: %s", LABELS[kind], exc, exc_info=True)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _is_ready(self, kind: str) -> bool:
        """Return True if the client of this kind exists and is LOADED."""
        client = getattr(self, f"_{kind}_client")
        return client is not None and client.state == ModelState.LOADED

    def _in_use(self, kind: str) -> bool:
        """Return True if the client of this kind exists and is running a call."""
        client = getattr(self, f"_{kind}_client")
        return client is not None and client.in_use

    def _load(self, kind: str, provider: Callable[[], Any], settings: Mapping[str, Any] | None) -> None:
        """Create the client if needed, apply and save settings, configure and initialize it; rejected loads change nothing."""
        label = LABELS[kind]
        with self._lock:
            if self._closed:
                raise RuntimeError("The server is shutting down.")
            if getattr(self, f"loading_{kind}_model"):
                raise RuntimeError(f"{label} is already loading.")
            if self._in_use(kind):
                raise RuntimeError(f"{label} is in use. Wait for the current task to finish.")
            setattr(self, f"loading_{kind}_model", True)

        try:
            client = getattr(self, f"_{kind}_client")
            if client is None:
                try:
                    client = provider()
                except Exception as exc:
                    setattr(self, f"{kind}_loading_error", str(exc))
                    logger.error("%s settings could not be loaded: %s", label, exc, exc_info=True)
                    raise
                setattr(self, f"_{kind}_client", client)

            if settings:
                client.config.from_frontend(settings)
                client.config.save()
                client.configure(client.config)

            logger.info("Loading %s: provider=%s", label, client.provider_id)
            try:
                client.initialize()
            except Exception as exc:
                setattr(self, f"{kind}_loading_error", str(exc))
                logger.error("%s load failed: provider=%s error=%s", label, client.provider_id, exc, exc_info=True)
                raise
            setattr(self, f"{kind}_loading_error", None)
            logger.info("%s loaded: provider=%s", label, client.provider_id)
        finally:
            with self._lock:
                setattr(self, f"loading_{kind}_model", False)

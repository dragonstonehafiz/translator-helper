from dataclasses import dataclass
from typing import ClassVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from llm.interface import LLMInterface
from models.config import Choice, ConfigField, DropdownOption, ModelConfig, NumberOption, TextOption, setting
from models.state import ModelState


@dataclass
class ChatGPTConfig(ModelConfig):
    """Settings for the OpenAI ChatGPT provider, saved to llm_chatgpt.json."""

    CONFIG_FILE: ClassVar[str] = "llm_chatgpt.json"
    PROVIDER: ClassVar[str] = "llm_chatgpt"
    TITLE: ClassVar[str] = "OpenAI ChatGPT"

    model_name: ConfigField[str] = setting("Model", DropdownOption((
        Choice("gpt-4.1-mini", "gpt-4.1-mini"),
        Choice("gpt-4.1", "gpt-4.1"),
        Choice("gpt-5.1", "gpt-5.1"),
        Choice("gpt-4o", "gpt-4o"),
        Choice("o4-mini", "o4-mini"),
    )), "gpt-4o", required=True)
    api_key: ConfigField[str] = setting("API Key", TextOption(password=True, placeholder="sk-..."), "", required=True)
    temperature: ConfigField[float] = setting("Temperature", NumberOption(min=0, max=2, step=0.1), 0.5)


class LLMChatGPT(LLMInterface[ChatGPTConfig]):
    """LLM backend that calls the OpenAI API via the LangChain ChatOpenAI client."""

    def __init__(self):
        """Load the saved ChatGPT settings."""
        super().__init__(ChatGPTConfig.load())
        self._llm = None

    def initialize(self) -> None:
        """Build the LangChain client and send a minimal test request to validate the API key."""
        try:
            self._llm = self._build_llm()
            self._build_llm(temperature=0, max_tokens=1).invoke([HumanMessage(content="ping")])
            self._state = ModelState.LOADED
        except Exception:
            self._llm = None
            self._state = ModelState.ERROR
            raise

    def shutdown(self) -> None:
        """Release the client reference."""
        self._llm = None
        self._state = ModelState.NOT_LOADED

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run inference; builds a temporary client when temperature or max_tokens override the defaults."""
        if self._llm is None:
            raise RuntimeError("ChatGPT client is not initialized.")
        llm = self._llm
        if temperature is not None or max_tokens is not None:
            llm = self._build_llm(temperature=temperature, max_tokens=max_tokens)

        messages = [HumanMessage(content=prompt)]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        return llm.invoke(messages).content

    def _build_llm(self, temperature: float | None = None, max_tokens: int | None = None) -> ChatOpenAI:
        """Construct a ChatOpenAI instance with the current model, API key and temperature."""
        if not self._config.api_key.value:
            raise ValueError("OpenAI API key is required to initialize ChatGPT.")

        params = {
            "api_key": self._config.api_key.value,
            "model": self._config.model_name.value,
            "temperature": self._config.temperature.value if temperature is None else temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        return ChatOpenAI(**params)

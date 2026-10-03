from dataclasses import dataclass
from typing import ClassVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from llm.interface import LLMInterface
from models.config import Choice, ConfigField, DropdownOption, ModelConfig, NumberOption, TextOption, setting
from models.state import ModelState

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass
class DeepSeekConfig(ModelConfig):
    """Settings for the DeepSeek API provider, saved to llm_deepseek.json."""

    CONFIG_FILE: ClassVar[str] = "llm_deepseek.json"
    PROVIDER: ClassVar[str] = "llm_deepseek"
    TITLE: ClassVar[str] = "DeepSeek"

    model_name: ConfigField[str] = setting("Model", DropdownOption((
        Choice("deepseek-v4-flash", "deepseek-v4-flash"),
        Choice("deepseek-v4-pro", "deepseek-v4-pro"),
    )), "deepseek-v4-flash", required=True)
    api_key: ConfigField[str] = setting("API Key", TextOption(password=True, placeholder="sk-..."), "", required=True)
    temperature: ConfigField[float] = setting("Temperature", NumberOption(min=0, max=2, step=0.1), 0.5)


class LLMDeepSeek(LLMInterface[DeepSeekConfig]):
    """LLM backend that calls the DeepSeek API via the OpenAI-compatible LangChain ChatOpenAI client."""

    def __init__(self):
        """Load the saved DeepSeek settings."""
        super().__init__(DeepSeekConfig.load())
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
            raise RuntimeError("DeepSeek client is not initialized.")
        llm = self._llm
        if temperature is not None or max_tokens is not None:
            llm = self._build_llm(temperature=temperature, max_tokens=max_tokens)

        messages = [HumanMessage(content=prompt)]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        return llm.invoke(messages).content

    def _build_llm(self, temperature: float | None = None, max_tokens: int | None = None) -> ChatOpenAI:
        """Construct a ChatOpenAI instance pointed at the DeepSeek API endpoint."""
        if not self._config.api_key.value:
            raise ValueError("DeepSeek API key is required to initialize DeepSeek.")

        params = {
            "api_key": self._config.api_key.value,
            "model": self._config.model_name.value,
            "base_url": DEEPSEEK_BASE_URL,
            "temperature": self._config.temperature.value if temperature is None else temperature,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        return ChatOpenAI(**params)

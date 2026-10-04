from dataclasses import dataclass
from typing import ClassVar

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from llm.interface import LLMInterface
from models.config import Choice, ConfigField, DropdownOption, ModelConfig, NumberOption, TextOption, setting
from models.state import ModelState


@dataclass
class ClaudeConfig(ModelConfig):
    """Settings for the Anthropic Claude provider, saved to llm_claude.json."""

    CONFIG_FILE: ClassVar[str] = "llm_claude.json"
    PROVIDER: ClassVar[str] = "llm_claude"
    TITLE: ClassVar[str] = "Anthropic Claude"

    model_name: ConfigField[str] = setting("Model", DropdownOption((
        Choice("Claude Haiku 4.5", "claude-haiku-4-5-20251001"),
        Choice("Claude Sonnet 4.6", "claude-sonnet-4-6"),
        Choice("Claude Opus 4.6", "claude-opus-4-6"),
    )), "claude-sonnet-4-6", required=True)
    api_key: ConfigField[str] = setting("API Key", TextOption(password=True, placeholder="sk-ant-..."), "", required=True)
    temperature: ConfigField[float] = setting("Temperature", NumberOption(min=0, max=1, step=0.1), 0.5)


class LLMClaude(LLMInterface[ClaudeConfig]):
    """LLM backend that calls the Anthropic Claude API via the LangChain ChatAnthropic client."""

    def __init__(self):
        """Load the saved Claude settings."""
        super().__init__(ClaudeConfig.load())
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

    def _infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run inference; builds a temporary client when temperature or max_tokens override the defaults."""
        if self._llm is None:
            raise RuntimeError("Claude client is not initialized.")
        llm = self._llm
        if temperature is not None or max_tokens is not None:
            llm = self._build_llm(temperature=temperature, max_tokens=max_tokens)

        messages = [HumanMessage(content=prompt)]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        return llm.invoke(messages).content

    def _build_llm(self, temperature: float | None = None, max_tokens: int | None = None) -> ChatAnthropic:
        """Construct a ChatAnthropic instance with the current model, API key and temperature."""
        if not self._config.api_key.value:
            raise ValueError("Anthropic API key is required to initialize Claude.")

        return ChatAnthropic(
            api_key=self._config.api_key.value,
            model=self._config.model_name.value,
            temperature=self._config.temperature.value if temperature is None else temperature,
            max_tokens=max_tokens if max_tokens is not None else 8096,
        )

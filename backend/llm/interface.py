from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from models.config import ModelConfig
from models.state import ModelState

ConfigT = TypeVar("ConfigT", bound=ModelConfig)


class LLMInterface(ABC, Generic[ConfigT]):
    """Contract every LLM provider satisfies: typed settings, a lifecycle state and inference."""

    def __init__(self, config: ConfigT):
        """Store the provider's settings; the client starts NOT_LOADED."""
        self._config = config
        self._state = ModelState.NOT_LOADED

    @property
    def provider_id(self) -> str:
        """Return the provider identifier declared by the config class."""
        return self._config.PROVIDER

    @property
    def config(self) -> ConfigT:
        """Return the provider's current settings."""
        return self._config

    @property
    def state(self) -> ModelState:
        """Return whether the client is initialized."""
        return self._state

    def configure(self, config: ConfigT) -> None:
        """Replace the settings; they take effect on the next initialize()."""
        self._config = config

    @abstractmethod
    def initialize(self) -> None:
        """Build the client from the current settings; sets LOADED, or ERROR and re-raises on failure."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """Release the client and return to NOT_LOADED."""
        raise NotImplementedError

    @abstractmethod
    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run one inference request; a failed request does not change the state."""
        raise NotImplementedError

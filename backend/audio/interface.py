from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import pysubs2

from models.config import ModelConfig
from models.state import ModelState

ConfigT = TypeVar("ConfigT", bound=ModelConfig)


class AudioModelInterface(ABC, Generic[ConfigT]):
    """Contract every audio transcription provider satisfies: typed settings, a lifecycle state and transcription."""

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
        """Return whether the model is initialized."""
        return self._state

    def configure(self, config: ConfigT) -> None:
        """Replace the settings; they take effect on the next initialize()."""
        self._config = config

    @abstractmethod
    def initialize(self) -> None:
        """Load the model from the current settings; sets LOADED, or ERROR and re-raises on failure."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """Release the model and return to NOT_LOADED."""
        raise NotImplementedError

    @abstractmethod
    def transcribe_line(self, audio_path: str, language: str) -> str:
        """Transcribe a short clip to one line of text."""
        raise NotImplementedError

    @abstractmethod
    def transcribe_file(self, audio_path: str, language: str) -> pysubs2.SSAFile:
        """Transcribe a full audio file to subtitles without saving them."""
        raise NotImplementedError

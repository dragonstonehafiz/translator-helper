from abc import ABC, abstractmethod


class LLMInterface(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize the LLM backend."""
        raise NotImplementedError

    @abstractmethod
    def change_model(self, model_name: str):
        """Swap or update the underlying model configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_model(self) -> str:
        """Return the current model identifier."""
        raise NotImplementedError

    @abstractmethod
    def configure(self, settings: dict):
        """Set provider-specific configuration values."""
        raise NotImplementedError

    @abstractmethod
    def get_settings_schema(self) -> dict:
        """Return a schema describing configurable settings."""
        raise NotImplementedError

    @abstractmethod
    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ):
        """Run inference with the current model."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> str:
        """Return current model status: 'loaded', 'not_loaded', or 'error'."""
        raise NotImplementedError

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the model is currently running a task."""
        raise NotImplementedError

    @abstractmethod
    def set_running(self, running: bool):
        """Set whether the model is currently running a task."""
        raise NotImplementedError

    @abstractmethod
    def set_device(self, device: str):
        """Set the device identifier for the model backend."""
        raise NotImplementedError

    @abstractmethod
    def get_device(self) -> str:
        """Return the current device identifier."""
        raise NotImplementedError

    @abstractmethod
    def set_temperature(self, temperature: float):
        """Set the default temperature for inference."""
        raise NotImplementedError

    @abstractmethod
    def get_temperature(self) -> float:
        """Return the current default temperature."""
        raise NotImplementedError

    @abstractmethod
    def get_server_variables(self) -> dict:
        """Return current server variables for status display."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self):
        """Release model resources."""
        raise NotImplementedError

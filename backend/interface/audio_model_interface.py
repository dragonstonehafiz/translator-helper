from abc import ABC, abstractmethod


class AudioModelInterface(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize the audio model backend."""
        raise NotImplementedError

    @abstractmethod
    def change_model(self, model_name: str):
        """Swap or update the underlying model configuration."""
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
    def transcribe_line(self, audio_path: str, language: str):
        """Transcribe audio to a single text line."""
        raise NotImplementedError

    @abstractmethod
    def transcribe_file(self, audio_path: str, language: str):
        """Transcribe audio to a subtitle file representation."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> str:
        """Return current model status: 'loaded', 'not_loaded', or 'error'."""
        raise NotImplementedError

    @abstractmethod
    def get_model(self) -> str:
        """Return the current model identifier."""
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
    def get_available_devices(self) -> dict:
        """Return available device options."""
        raise NotImplementedError

    @abstractmethod
    def get_server_variables(self) -> dict:
        """Return current server variables for status display."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self):
        """Release model resources."""
        raise NotImplementedError

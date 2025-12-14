"""
Settings management for Translator Helper backend.
Loads configuration from .env file with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    tavily_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    temperature: float = 0.5
    whisper_model: str = "tiny"
    device: str = "cpu"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

"""Lifecycle state shared by every model provider."""

from enum import Enum


class ModelState(Enum):
    """Whether a provider client is initialized; owned and updated by the provider itself."""

    NOT_LOADED = "not_loaded"
    LOADED = "loaded"
    ERROR = "error"

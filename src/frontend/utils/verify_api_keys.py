"""Helpers for validating configured API keys."""

import streamlit as st

from src.backend.utils import (
    validate_openai_api_key,
    validate_tavily_api_key,
)


def guard_api_keys() -> None:
    """Ensure required API keys exist and are valid before continuing."""
    errors = []

    openai_key = st.session_state.get("openai_api_key", "")
    if not openai_key:
        errors.append("OpenAI API key is missing.")
    elif not validate_openai_api_key(openai_key):
        errors.append("OpenAI API key appears invalid.")

    tavily_key = st.session_state.get("tavily_api_key", "")
    if not tavily_key:
        errors.append("Tavily API key is missing.")
    elif not validate_tavily_api_key(tavily_key):
        errors.append("Tavily API key appears invalid.")

    if errors:
        st.error(
            "API key validation failed:\n- " + "\n- ".join(errors)
        )
        st.stop()

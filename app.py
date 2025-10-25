"""Streamlit entry point for Translator Helper UI."""

import streamlit as st

from src.backend.utils import load_config
from src.frontend.pages import (
    render_context_page,
    render_settings_page,
    render_transcribe_page,
    render_translate_page,
)
from src.frontend.utils import ensure_session_defaults, guard_dependencies, guard_api_keys, load_models_to_session_state

PAGE_RENDERERS = {
    "Settings": render_settings_page,
    "Translate": render_translate_page,
    "Transcribe": render_transcribe_page,
    "Context": render_context_page,
}


def run_app() -> None:
    """Configure Streamlit and render the selected page."""
    st.set_page_config(page_title="Translator Helper", layout="wide")

    guard_dependencies()
    ensure_session_defaults()

    config = load_config("config.json")
    st.session_state.update(config)

    ensure_session_defaults()
    guard_api_keys()
    load_models_to_session_state()

    st.title("Translator Helper")
    st.caption("Choose a workflow from the sidebar to get started.")

    st.sidebar.title("Navigation")
    selected_page = st.sidebar.selectbox("Page", list(PAGE_RENDERERS.keys()))

    render_page = PAGE_RENDERERS[selected_page]
    render_page()


if __name__ == "__main__":
    run_app()


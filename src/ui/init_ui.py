import streamlit as st

DEFAULTS = {
    "input_lang": "ja",
    "output_lang": "en",
    "whisper_model": "medium",
    "openai_model": "gpt-4o",
    "device": "cpu",
    "openai_api_key": "",
    "tavily_api_key": "",
    "temperature": 0.7,
    "whisper_instance": None,
    "gpt_instance": None
}

def init_session_state_defaults():
    """Ensures all expected keys exist in session_state, using defaults for any missing ones."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
            
def init_session_state_from_config(config: dict):
    st.session_state["input_lang"] = config.get("input_lang", "ja")
    st.session_state["output_lang"] = config.get("output_lang", "en")
    st.session_state["whisper_model"] = config.get("whisper_model", "medium")
    st.session_state["openai_api_key"] = config.get("openai_api_key", "")
    st.session_state["openai_model"] = config.get("openai_model", "gpt-4o")
    st.session_state["tavily_api_key"] = config.get("tavily_api_key", "")
    st.session_state["temperature"] = config.get("temperature", 0.7)
    st.session_state["device"] = config.get("device", "cpu")
            

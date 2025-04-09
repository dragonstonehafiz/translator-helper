import streamlit as st

DEFAULTS = {
    "selected_model_transcribe": "medium",
    "input_lang": "ja",
    "enable_cuda": False,
    "whisper_model": None,
    "openai_api_key": "",
    "openai_api_key_valid": False,
    "openai_api_client": None,
    "source_lang_translate": "ja",
    "target_lang_translate": "en",
    "model_translate": "gpt-4o",
    "temperature": 1.0,
    "top_p": 1.0,
    "context_scene_backstory": "",
    "context_characters": "",
    "context_tone": ""
}

def initialize_session_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

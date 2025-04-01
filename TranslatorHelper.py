import streamlit as st
from src.ui_transcribe import render_transcribe
from src.ui_translate import render_translate
from src.ui_grade import render_grade
from src.ui_config import render_config, load_config, render_load_whisper_model, render_test_api_key
from src.session_defaults import initialize_session_state
from src.session_setup import create_client

# fix RuntimeError: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
import torch
torch.classes.__path__ = []

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

if __name__ == "__main__":
    st.set_page_config(
        page_title="Translation Helper",  # Sets the title of the page
        page_icon="🇯🇵",  # Sets the favicon/icon of the page
        layout="centered",  # Options: "centered" or "wide"
    )
    
    initialize_session_state()
    if not load_config():
        st.warning("No configuration file found. Default settings will be used.")
    else:
        # This if statement is so we don't run this line every time the page is refreshed
        if st.session_state.whisper_model is None:
            render_load_whisper_model()
        
        if st.session_state.openai_api_client is None:
            render_test_api_key()
            if st.session_state.openai_api_key_valid:
                st.session_state.openai_api_client = create_client(st.session_state.openai_api_key)
        
        st.success("Configuration loaded successfully.")
    
    st.title('Translator Helper')
    tab_transcribe, tab_translate, tab_grade, tab_config = st.tabs(["Transcribe", "Translate", "Grade", "Configuration"])

    with tab_transcribe:
        render_transcribe()
    with tab_translate:
        render_translate()
    with tab_grade:
        render_grade()
    with tab_config:
        render_config()
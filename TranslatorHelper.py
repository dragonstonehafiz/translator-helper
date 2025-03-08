import streamlit as st
from src.ui_transcribe import render_transcribe, load_whisper_model
from src.ui_translate import render_translate
from src.ui_grade import render_grade
from src.ui_config import render_config, create_sessions_var

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
    
    create_sessions_var()
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
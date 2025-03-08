import streamlit as st
from src.ui_transcribe import render_transcribe, load_whisper_model
from src.ui_translate import render_translate
from src.ui_grade import render_grade

# fix RuntimeError: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
import torch
torch.classes.__path__ = []

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

def create_sessions_var():
    # Initialize session state for settings if not set
    if "selected_model_transcribe" not in st.session_state:
        st.session_state.selected_model_transcribe = "tiny"
    if "input_lang" not in st.session_state:
        st.session_state.input_lang = "ja"
    if "device" not in st.session_state:
        st.session_state.device = "cpu"
    if "whisper_model" not in st.session_state:
        load_whisper_model()
        
if __name__ == "__main__":
    create_sessions_var()
    st.title('Translator Helper')
    tab_transcribe, tab_translate, tab_grade = st.tabs(["Transcribe", "Translate", "Grade"])

    with tab_transcribe:
        render_transcribe()
    with tab_translate:
        render_translate()
    with tab_grade:
        render_grade()
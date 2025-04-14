import streamlit as st

from src.ui.config import tab_config
from src.ui.init import init_session_state_defaults, init_session_state_from_config
from src.ui.load_models import ui_load_whisper_model, ui_load_openai_api, ui_load_tavily_api
from src.ui.context import tab_context
from src.ui.transcribe import tab_transcribe
from src.ui.translate import tab_translate
from src.ui.grade import tab_grade


from src.logic.config import load_config

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
    st.title('Translator Helper')
    
    # Initialize session state once
    if "initialized_config" not in st.session_state:
        init_session_state_defaults()
        config = load_config("config.json")
        init_session_state_from_config(config)
        st.session_state["initialized_config"] = True
        ui_load_whisper_model(st.session_state.get("whisper_model", "medium"))
        ui_load_tavily_api(st.session_state.get("tavily_api_key", "PLEASE FILL IN"))
        ui_load_openai_api(api_key=st.session_state.get("openai_api_key", "PLEASE FILL IN"), 
                           model_name=st.session_state.get("openai_model", "gpt-4o"),
                           temp=st.session_state.get("temperature", 0.5))
    
    config, context, transcribe, translate, grade = st.tabs(["Configuration", "Context", "Transcribe", "Translate", "Grade"])

    with config:
        tab_config()
    with context:
        tab_context()
    with transcribe:
        tab_transcribe()
    with translate:
        tab_translate()
    with grade:
        tab_grade()

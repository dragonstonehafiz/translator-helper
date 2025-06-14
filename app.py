import streamlit as st

from src.ui.config_ui import tab_config
from src.ui.init_ui import init_session_state_defaults, init_session_state_from_config
from src.ui.load_models_ui import ui_load_whisper_model, ui_load_openai_api, ui_load_tavily_api
from src.ui.context_ui import tab_context
from src.ui.transcribe_ui import tab_transcribe_line, tab_transcribe_file
from src.ui.translate_ui import tab_translate, tab_translate_file
from src.ui.grade_ui import tab_grade


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
        
    mode = st.sidebar.radio("Pages", ["Settings", "Automation", "Assistant"], index=0)
    
    if mode == "Settings":
        tab_config()
        
    elif mode == "Automation":
        context, transcribe_file, translate_file = st.tabs(["Context", "Transcribe File", "Translate File"])
        
        with context:
            tab_context()
        with transcribe_file:
            tab_transcribe_file()
        with translate_file:
            tab_translate_file()
        
    elif mode == "Assistant":
        transcribe, translate, grade = st.tabs(["Transcribe", "Translate", "Grade"])
        
        with transcribe:
            tab_transcribe_line()
        with translate:
            tab_translate()
        with grade:
            tab_grade()

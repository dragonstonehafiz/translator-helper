import sys
# This is a workaround for running the script from the parent directory
sys.path.append('../')

import streamlit as st
from src.logic.load_models import load_whisper_model, load_gpt_model, load_web_searcher
from src.logic.validate_api_keys import validate_openai_api_key, validate_tavily_api_key

def ui_load_whisper_model(model_name: str):
    # Load and store whisper model in session_state
    with st.spinner(f"Loading Whisper model: {model_name}..."):
        model = load_whisper_model(model_name, device=st.session_state.get("device", "cpu"))
        st.session_state["whisper_instance"] = model
    st.success("Whisper model loaded and stored in session state.")
    
    
def ui_load_openai_api(api_key: str, model_name: str, temp: float = 0.7):
    with st.spinner(f"Loading ChatOpenAI model: {model_name}..."):
        if not validate_openai_api_key(api_key):
            st.error("OpenAI API Key is not valid.")
            st.session_state["gpt_instance"] = None
        else:
            llm = load_gpt_model(api_key, model_name, temp)
            st.session_state["gpt_instance"] = llm
            st.success("ChatOpenAI model loaded and stored in session state.")
            
        
def ui_load_tavily_api(api_key):
    with st.spinner(f"Loading Tavily API..."):
        web_search = load_web_searcher(api_key)
        st.session_state["web_search_instance"] = web_search
        st.success("Tavily model loaded and stored in session state.")
            

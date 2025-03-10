import streamlit as st
import whisper
import openai
from src.translate import create_client
import torch

# To remove FutureWarning
import functools
whisper.torch.load = functools.partial(whisper.torch.load, weights_only=True)

def create_sessions_var():
    # Audio Transcription
    if "selected_model_transcribe" not in st.session_state:
        st.session_state.selected_model_transcribe = "medium"
    if "input_lang" not in st.session_state:
        st.session_state.input_lang = "ja"
    if "enable_cuda" not in st.session_state:
        st.session_state.enable_cuda = False 
    if "whisper_model" not in st.session_state:
        st.session_state.whisper_model = None  # Now requires manual loading
    # Translation
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = ""
    if "openai_api_key_valid" not in st.session_state:
        st.session_state.openai_api_key_valid = False
    if "openai_api_client" not in st.session_state:
        st.session_state.openai_api_client = None
    if "source_lang_translate" not in st.session_state:
        st.session_state.source_lang_translate = "ja"
    if "target_lang_translate" not in st.session_state:
        st.session_state.target_lang_translate = "en"
    if "model_translate" not in st.session_state:
        st.session_state.model_translate = "gpt-4o-mini"
    if "temperature" not in st.session_state:
        st.session_state.temperature = 1.0
    if "top_p" not in st.session_state:
        st.session_state.top_p = 1.0
    

def load_whisper_model(selected_model: str = None): 
    if selected_model is not None:
        st.session_state.selected_model_transcribe = selected_model
    device = "cuda" if st.session_state.enable_cuda else "cpu"
    try:
        with st.spinner("Loading Whisper model... This may take a while. Your first time using a model will take longer to load as it need to be downloaded."):
            st.session_state.whisper_model = whisper.load_model(st.session_state.selected_model_transcribe, device=device)
    except torch.cuda.OutOfMemoryError:
        st.error("CUDA ran out of memory. Try using a smaller model or disabling CUDA.")
        st.session_state.enable_cuda = False 
        
def render_audio_config(page_name: str):
    
    leftcol, rightcol = st.columns(2)
    
    # Model Selection
    with leftcol:
        model_options = ["tiny", "base", "small", "medium", "large"]
        st.session_state.selected_model_transcribe = st.selectbox("Select Whisper Model:", model_options, 
                                      index=model_options.index(st.session_state.selected_model_transcribe),
                                      key=f"{page_name} whisper model")
    
    # Language Selection
    with rightcol:
        st.session_state.input_lang = st.text_input("Input Language", 
                                                    st.session_state.input_lang, 
                                                    key=f"{page_name} input lang")
    
    # Enable CUDA Option
    st.session_state.enable_cuda = st.checkbox("Enable GPU Acceleration", st.session_state.enable_cuda, key=f"{page_name} enable cuda")
    st.warning("You must reload the model when enabling/disabling.")
    st.warning("Check [here](https://github.com/openai/whisper) to make sure you have enough VRAM for the model you want to use.")
    
    # Load Model
    if st.button("Load Whisper Model", key=f"{page_name} load whisper model"):
        load_whisper_model()

def test_api_key(api_key):
    with st.spinner("Checking API Key"):
        try:
            client = openai.OpenAI(api_key=api_key)
            client.models.list()
            return True
        except openai.OpenAIError:
            return False

def render_translate_config(page_name: str):
    # API KEY
    api_key_input = st.text_input("Enter OpenAI API Key:", 
                                  st.session_state.openai_api_key, 
                                  type="password", 
                                  key=f"{page_name} translate api key")
    
    # Check if API key has changed before validating
    if api_key_input != st.session_state.openai_api_key:
        st.session_state.openai_api_key = api_key_input
        
        if st.session_state.openai_api_key.strip() == "":
            st.session_state.openai_api_key_valid = False
        else:
            if not test_api_key(st.session_state.openai_api_key):
                st.session_state.openai_api_key_valid = False
            else:
                st.session_state.openai_api_key_valid = True

    if st.session_state.openai_api_key_valid:
        st.success("API Key is valid")
    else:
        st.error("⚠ API Key is invalid")
        
    
    # Model Selection
    model_options = ["gpt-4", "gpt-4o", "gpt-4o-mini"]
    st.session_state.model_translate = st.selectbox("Select Model:", 
                                                    model_options, 
                                                    index=model_options.index(st.session_state.model_translate),
                                                    key=f"{page_name} translate model")
    
    if st.button("Load OpenAI API client", 
                 disabled=not st.session_state.openai_api_key_valid,
                 key=f"{page_name} load client"):
        st.session_state.openai_api_client = create_client(st.session_state.openai_api_key)
    
    # Temperature and Top-p Selection
    temp_col, top_p_col = st.columns(2)
    with temp_col:
        st.session_state.temperature = st.number_input("Temperature (0 - 2):", 
                                                        min_value=0.0, max_value=2.0, 
                                                        value=st.session_state.temperature, 
                                                        step=0.1,
                                                        key=f"{page_name} temperature")
    with top_p_col:
        st.session_state.top_p = st.number_input("Top-p (0 - 2):", 
                                                min_value=0.0, max_value=2.0, 
                                                value=st.session_state.top_p, 
                                                step=0.1,
                                                key=f"{page_name} top p")

        
    # Language Selection
    leftcol, rightcol = st.columns(2)
    with leftcol:
        st.session_state.source_lang_translate = st.text_input("Enter Source Language:", 
                                                                st.session_state.source_lang_translate,
                                                                key=f"{page_name} translate source lang")
    with rightcol:
        st.session_state.target_lang_translate = st.text_input("Enter Target Language:", 
                                                                st.session_state.target_lang_translate,
                                                                key=f"{page_name} translate target lang")
    


def render_config():
    st.header("Configuration")
    
    st.subheader("Transcribe")
    render_audio_config("config page")
    
    st.subheader("Translate")
    render_translate_config("config page")
    
    
    
    
import streamlit as st
import whisper
import json

from src.session_setup import load_whisper_model, create_client, test_api_key

# To remove FutureWarning
import functools
whisper.torch.load = functools.partial(whisper.torch.load, weights_only=True)
    
def render_load_whisper_model():
    with st.spinner("Loading Whisper model... This may take a while. Your first time using a model will take longer to load model needs to be downloaded."):
        st.session_state.whisper_model = load_whisper_model(st.session_state.selected_model_transcribe)
        if st.session_state.whisper_model is not None:
            st.success("Whisper model loaded successfully.")
        else:
            st.error("Failed to load Whisper model. Please check the Config page.")
        
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
        render_load_whisper_model()

def render_test_api_key():
    with st.spinner("Checking API Key"):
        st.session_state.openai_api_key_valid = test_api_key(st.session_state.openai_api_key)
        
        if st.session_state.openai_api_key_valid:
            st.success("API Key is valid")
        else:
            st.error("API Key is invalid")

def render_translate_config(page_name: str):
    # API KEY
    api_key_input = st.text_input(
        "Enter OpenAI API Key:", 
        value=st.session_state.openai_api_key, 
        placeholder="sk-...", 
        type="password", 
        key=f"{page_name} translate api key"
    )
    
    # Check if API key has changed before validating
    if api_key_input != st.session_state.openai_api_key:
        print(st.session_state.openai_api_key)
        st.session_state.openai_api_key = api_key_input
        print(st.session_state.openai_api_key)
        
        if st.session_state.openai_api_key.strip() == "":
            st.session_state.openai_api_key_valid = False
        else:
            render_test_api_key()
        
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
        st.session_state.source_lang_translate = st.text_input(
            "Enter Source Language:",
            value=st.session_state.source_lang_translate,
            placeholder="e.g. ja",
            key=f"{page_name} translate source lang"
        )
    with rightcol:
        st.session_state.target_lang_translate = st.text_input(
            "Enter Target Language:",
            value=st.session_state.target_lang_translate,
            placeholder="e.g. en",
            key=f"{page_name} translate target lang"
        )
    
def render_config():
    st.header("Configuration")
    
    st.subheader("Save/Load")
    if st.button("Save Configurations"):
        save_config()
    
    st.subheader("Transcribe")
    render_audio_config("config page")
    
    st.subheader("Translate")
    render_translate_config("config page")
    
def save_config(path="config.json"):
    keys_to_save = [
        "selected_model_transcribe", "input_lang", "enable_cuda",
        "openai_api_key", "source_lang_translate", "target_lang_translate",
        "model_translate", "temperature", "top_p"
    ]
    config = {key: st.session_state.get(key) for key in keys_to_save}
    print(config)
    # if not os.path.exists(path):
    file = open(path, "w", encoding="utf-8")
    json.dump(config, file, ensure_ascii=False, indent=4)
    
def load_config(path="config.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        st.session_state.initialized = True
        for key, value in config.items():
            st.session_state[key] = value
        return True
    except FileNotFoundError:
        st.warning(f"No config file found at {path}")
        return False
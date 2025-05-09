import sys
sys.path.append('../')

import streamlit as st
from src.logic.load_models import get_device_map
from src.logic.config import save_config, load_config
from src.ui.load_models_ui import ui_load_whisper_model, ui_load_openai_api, ui_load_tavily_api
from src.ui.init_ui import init_session_state_from_config

def tab_config():
    st.header("Configuration")
    
    st.subheader("General")
    # Load and Save Configurations
    left, right = st.columns(2) 
    with left:
        if st.button("Load Configuration", use_container_width=True):
            config = load_config()
            init_session_state_from_config(config)
            st.success("Configuration loaded from config.json.")
            st.rerun()
    with right:
        if st.button("Save Configuration", use_container_width=True):
            config = {
                "input_lang": st.session_state["input_lang"],
                "output_lang": st.session_state["output_lang"],
                "whisper_model": st.session_state["whisper_model"],
                "device": st.session_state["device"],
                "openai_model": st.session_state["openai_model"],
                "openai_api_key": st.session_state["openai_api_key"],
                "tavily_api_key": st.session_state["tavily_api_key"],
                "temperature": st.session_state["temperature"],
            }
            save_config(config)
            st.success("Configuration saved to config.json.")

    # Input and Output Language
    col1, col2 = st.columns(2)
    with col1:
        input_lang = st.text_input("Input Language", value=st.session_state.get("input_lang", "ja"))
    with col2:
        output_lang = st.text_input("Output Language", value=st.session_state.get("output_lang", "en"))

    st.subheader("Transcription")
    # Whisper model + Load
    col1, col2 = st.columns(2)
    with col1:
        whisper_model = st.selectbox(
            "Select Whisper Model",
            options=["tiny", "base", "small", "medium", "large", "turbo"],
            index=["tiny", "base", "small", "medium", "large", "turbo"].index(
                st.session_state.get("whisper_model", "medium")
            ),
            help="Choose the Whisper model to use for transcription."
        )
    with col2:
        # devices = get_available_devices()
        # selected_label = st.selectbox(
        #     "Select CPU/GPU",
        #     options=devices,
        #     index=devices.index(st.session_state.get("device", "cpu")),
        #     help="Choose whether you want to use GPU acceleration or not."
        # )
        # # Extract "cpu" or "cuda:X"
        # device_id = selected_label.split(" - ")[0].strip()
        # st.session_state["device"] = device_id
        device_map = get_device_map()
        device_labels = list(device_map.keys())
        selected_label = st.selectbox(
            "Select CPU/GPU",
            options=device_labels,
            index=device_labels.index(next((k for k, v in device_map.items() if v == st.session_state.get("device", "cpu")), "cpu")),
            help="Choose whether you want to use GPU acceleration or not."
        )

        # Save valid device string to session
        device = device_map[selected_label]
        
    if st.button("Load Whisper", use_container_width=True):
        ui_load_whisper_model(whisper_model)

    st.subheader("OpenAI Configurations")
    # OpenAI model selection
    left, right = st.columns([3, 1])
    openai_model = st.selectbox(
        "OpenAI Model",
        options=["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
        index=["gpt-3.5-turbo", "gpt-4", "gpt-4o"].index(
            st.session_state.get("openai_model", "gpt-4o")
        ),
        help="Select which OpenAI model to use for LangChain processing."
    )
                
    # Temperature
    temperature = st.slider(
        "Model Temperature",
        min_value=0.0,
        max_value=1.5,
        value=st.session_state.get("temperature", 0.7),
        step=0.1
    )
    
    st.subheader("API Keys")
    # API Keys
    left, right = st.columns(2)
    with left:
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.get("openai_api_key", "")
        )
    with right:
        tavily_api_key = st.text_input(
            "Tavily API Key",
            type="password",
            value=st.session_state.get("tavily_api_key", "")
        )
        
    left, right = st.columns(2)
    with left:
        if st.button("Load OpenAI API", use_container_width=True):
            ui_load_openai_api(api_key=openai_api_key, model_name=openai_model, temp=temperature)
    with right:
        if st.button("Load Tavily API", use_container_width=True):
            ui_load_tavily_api(api_key=tavily_api_key)

    # Sync values to session state
    st.session_state["input_lang"] = input_lang
    st.session_state["output_lang"] = output_lang
    st.session_state["whisper_model"] = whisper_model
    st.session_state["openai_model"] = openai_model
    st.session_state["openai_api_key"] = openai_api_key
    st.session_state["tavily_api_key"] = tavily_api_key
    st.session_state["temperature"] = temperature
    st.session_state["device"] = device

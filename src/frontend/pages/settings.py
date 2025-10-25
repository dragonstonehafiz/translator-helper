import streamlit as st

from src.backend.utils import get_device_map, save_config


def _save_config_snapshot() -> None:
    """Persist the current session-state configuration to disk."""
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


def _auto_save_notice() -> None:
    st.toast("Settings saved.")


def render_settings_page() -> None:
    st.title("Settings")
    st.caption("Adjust runtime configuration. Changes are saved automatically.")

    col1, col2 = st.columns(2)
    with col1:
        input_lang = st.text_input(
            "Input Language",
            value=st.session_state.get("input_lang", "ja"),
            help="Source language code (e.g., 'ja').",
        )
    with col2:
        output_lang = st.text_input(
            "Output Language",
            value=st.session_state.get("output_lang", "en"),
            help="Target language code (e.g., 'en').",
        )

    col3, col4 = st.columns(2)
    with col3:
        whisper_model = st.selectbox(
            "Whisper Model",
            options=["tiny", "base", "small", "medium", "large", "turbo"],
            index=["tiny", "base", "small", "medium", "large", "turbo"].index(
                st.session_state.get("whisper_model", "turbo")
            ),
        )
    with col4:
        device_map = get_device_map()
        device_labels = list(device_map.keys())
        current_device = st.session_state.get("device", "cpu")
        selected_label = st.selectbox(
            "Device",
            options=device_labels,
            index=device_labels.index(
                next((label for label, dev in device_map.items() if dev == current_device), "cpu")
            ),
        )
        device = device_map[selected_label]

    col5, col6, col7 = st.columns([1, 2, 1])
    with col5:
        openai_model = st.selectbox(
            "OpenAI Model",
            options=["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
            index=["gpt-3.5-turbo", "gpt-4", "gpt-4o"].index(
                st.session_state.get("openai_model", "gpt-4o")
            ),
        )
    with col6:
        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.get("openai_api_key", ""),
            type="password",
            help="Stored securely in session state/config.json.",
        )
    with col7:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.5,
            value=float(st.session_state.get("temperature", 0.7)),
            step=0.1,
        )

    tavily_api_key = st.text_input(
        "Tavily API Key",
        value=st.session_state.get("tavily_api_key", ""),
        type="password",
    )

    if st.button("Save Settings", use_container_width=True):
        st.session_state["input_lang"] = input_lang
        st.session_state["output_lang"] = output_lang
        st.session_state["whisper_model"] = whisper_model
        st.session_state["device"] = device
        st.session_state["openai_model"] = openai_model
        st.session_state["openai_api_key"] = openai_api_key
        st.session_state["temperature"] = temperature
        st.session_state["tavily_api_key"] = tavily_api_key

        _save_config_snapshot()
        _auto_save_notice()

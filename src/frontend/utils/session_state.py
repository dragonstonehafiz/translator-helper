import streamlit as st

from src.backend.utils import load_gpt_model, load_tavily_api, load_whisper_model

DEFAULT_SESSION_VALUES = {
    "input_lang": "ja",
    "output_lang": "en",
    "whisper_model": "turbo",
    "device": "cuda:0",
    "openai_model": "gpt-4o",
    "openai_api_key": "",
    "tavily_api_key": "",
    "temperature": 0.7,
    "whisper_instance": None,
    "gpt_instance": None,
    "web_search_instance": None,
}

def ensure_session_defaults() -> None:
    """Populate Streamlit session_state with default values if missing."""
    for key, value in DEFAULT_SESSION_VALUES.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_models_to_session_state() -> None:
    """Load or refresh model instances only when their configuration changes."""
    signature_key = "_model_signature"
    current_signature = {
        "whisper": (
            st.session_state.get("whisper_model"),
            st.session_state.get("device"),
        ),
        "gpt": (
            st.session_state.get("openai_api_key"),
            st.session_state.get("openai_model"),
            st.session_state.get("temperature"),
        ),
        "tavily": (st.session_state.get("tavily_api_key"),),
    }
    previous_signature = st.session_state.get(signature_key, {})

    if (
        st.session_state.get("whisper_instance") is None
        or previous_signature.get("whisper") != current_signature["whisper"]
    ):
        with st.spinner(f"Loading Whisper model: {st.session_state['whisper_model']}..."):
            st.session_state["whisper_instance"] = load_whisper_model(
                st.session_state["whisper_model"],
                device=st.session_state.get("device", "cpu"),
            )

    if (
        st.session_state.get("gpt_instance") is None
        or previous_signature.get("gpt") != current_signature["gpt"]
    ):
        with st.spinner(f"Loading OpenAI model: {st.session_state['openai_model']}..."):
            st.session_state["gpt_instance"] = load_gpt_model(
                st.session_state["openai_api_key"],
                model_name=st.session_state["openai_model"],
                temperature=st.session_state["temperature"],
            )

    if (
        st.session_state.get("web_search_instance") is None
        or previous_signature.get("tavily") != current_signature["tavily"]
    ):
        with st.spinner("Loading Tavily search client..."):
            st.session_state["web_search_instance"] = load_tavily_api(
                st.session_state["tavily_api_key"]
            )

    st.session_state[signature_key] = current_signature

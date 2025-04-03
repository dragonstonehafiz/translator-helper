import streamlit as st
from src.translate import translate
from src.ui_context import get_context_dict, render_context_dict
import streamlit as st

def render_translate():
    st.header("Translate")

    st.subheader("Context")
    context_dict = get_context_dict()
    render_context_dict(context_dict)

    st.subheader("Input")
    text_to_translate = ""
    if st.session_state.openai_api_client is None:
        st.error("OpenAI API client not loaded. Please load it in the Configurations page.")
    else:
        # Text Input for Translation
        text_to_translate = st.text_area("Enter Text to Translate:")
        client = st.session_state.openai_api_client

    # Boolean to disable button
    has_text = text_to_translate.strip() != ""

    if st.button("Translate", disabled=not has_text, key="translate_button"):
        with st.spinner("Translating... This may take a while."):
            translated_text = translate(client, text_to_translate, model=st.session_state.model_translate, 
                                        input_lang=st.session_state.source_lang_translate, 
                                        target_lang=st.session_state.target_lang_translate,
                                        temperature=st.session_state.temperature,
                                        top_p=st.session_state.top_p,
                                        context=context_dict)
            render_translated_text(translated_text)


def render_translated_text(translated_text):
    # Basic markdown parsing
    parts = {
        "Naturalized Translation": "",
        "Literal Translation": "",
        "Annotated Translation": ""
    }
    current = None
    for line in translated_text.splitlines():
        if "Naturalized Translation" in line:
            current = "Naturalized Translation"
        elif "Literal Translation" in line:
            current = "Literal Translation"
        elif "Annotated Translation" in line:
            current = "Annotated Translation"
        elif current:
            parts[current] += line + "\n"

    st.subheader("Translation Output")

    for label, content in parts.items():
        st.markdown(f"#### {label}")
        st.markdown(
            f"""
            <div style='
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 0.75rem;
                border-radius: 0.5rem;
                font-family: monospace;
                white-space: pre-wrap;
                word-wrap: break-word;
                overflow-x: auto;
            '>{content.strip()}</div>
            """,
            unsafe_allow_html=True
        )


import streamlit as st
import sys
sys.path.append('../')

from src.logic.translate import translate_multi_response
from src.ui.shared_ui import show_context, create_context_dict

def tab_translate():
    st.header("Translate")
    
    show_context()
        
    st.subheader("Input")
    input_text = st.text_area("Text to Translate", value=st.session_state.get("raw_input_text", ""))
    st.session_state["raw_input_text"] = input_text
    
    if st.session_state["gpt_instance"] is None:
        st.error("Please load a the OpenAI API to use this functionality.")
        return
    
    if st.button("Translate", use_container_width=True):
        llm = st.session_state.get("gpt_instance")

        if not llm:
            st.error("OpenAI model is not loaded.")
        elif not input_text.strip():
            st.warning("Please enter some text to translate.")
        else:
            with st.spinner("Translating..."):
                translation = translate_multi_response(
                    llm=st.session_state["gpt_instance"],
                    text=st.session_state["raw_input_text"],
                    context=create_context_dict(),
                    input_lang=st.session_state.get("input_lang", "ja"),
                    target_lang=st.session_state.get("output_lang", "en")
                )

                st.session_state["translated_output"] = translation
                
    translation = st.session_state.get("translated_output", "")
    render_translated_text(translation)
                

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


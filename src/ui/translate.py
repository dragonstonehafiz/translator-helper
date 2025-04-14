import streamlit as st
import sys
sys.path.append('../')

from src.logic.translate import translate
from src.ui.shared import show_context, create_context_dict

def tab_translate():
    st.header("Translate")
    
    show_context()
        
    st.subheader("Input")
    input_text = st.text_area("Text to Translate", value=st.session_state.get("raw_input_text", ""))
    st.session_state["raw_input_text"] = input_text
    
    if st.button("Translate", use_container_width=True):
        llm = st.session_state.get("gpt_instance")

        if not llm:
            st.error("OpenAI model is not loaded.")
        elif not input_text.strip():
            st.warning("Please enter some text to translate.")
        else:
            with st.spinner("Translating..."):
                # This is where you'd build your actual prompt
                # Here's a very simple version just for testing
                prompt = f"Translate this from Japanese to English:\n\n{input_text.strip()}"
                response = llm.invoke(prompt)
                translation = response.content
                translation = translate(
                    llm=st.session_state["gpt_instance"],
                    text=st.session_state["raw_input_text"],
                    context=create_context_dict(),
                    input_lang=st.session_state["input_lang"],
                    target_lang=st.session_state["output_lang"]
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


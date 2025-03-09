import streamlit as st
from src.ui_config import render_translate_config
from src.translate import grade

def render_grade():
    st.header("Grade")
    
    st.subheader("Configuration")
    render_translate_config("grade page")

    st.subheader("Provide Input")
    if st.session_state.openai_api_client is None:
        st.error("OpenAI API client not loaded.")
    else:
        # Text Inputs
        original_text = st.text_area("Enter Original Text:")
        translated_text = st.text_area("Enter Translated Text:")
        client = st.session_state.openai_api_client
        # Grade Button
        if st.button("Grade Translation"):
            if not original_text.strip() or not translated_text.strip():
                st.error("Both fields must be filled in before grading.")
            else:
                with st.spinner("Grading translation... This may take a while."):
                    grading_result = grade(client, original_text, translated_text,
                                            model=st.session_state.model_translate,
                                            input_lang=st.session_state.source_lang_translate,
                                            target_lang=st.session_state.target_lang_translate,
                                            temperature=st.session_state.temperature,
                                            top_p=st.session_state.top_p)
                    
                    st.subheader("Translation Grade:")
                    st.markdown(grading_result)
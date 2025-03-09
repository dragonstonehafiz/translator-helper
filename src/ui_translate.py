import streamlit as st
from src.ui_config import render_translate_config
from src.translate import translate

def render_translate():
    st.header("Translate")
    
    st.subheader("Config")
    render_translate_config("translate page")
    
    st.subheader("Provide Input Sentence")
    
    if st.session_state.openai_api_client is None:
        st.error("OpenAI API client not loaded. Check configurations.")
    else:
        # Text Input for Translation
        text_to_translate = st.text_area("Enter Text to Translate:")
        client = st.session_state.openai_api_client
        
        if client is None:
            st.error("OpenAI API client not loaded")
        elif text_to_translate != "" and st.button("Translate"):
            with st.spinner("Translating... This may take a while."):
                translated_text = translate(client, text_to_translate, model=st.session_state.model_translate, 
                                            input_lang=st.session_state.source_lang_translate, 
                                            target_lang=st.session_state.target_lang_translate,
                                            temperature=st.session_state.temperature,
                                            top_p=st.session_state.top_p)
                st.markdown(translated_text)
import streamlit as st
from src.translate import translate

def render_translate():
    st.header("Translate")
    
    if st.session_state.openai_api_client is None:
        st.error("OpenAI API client not loaded. Please load it in the Configurations page.")
    else:
        # Text Input for Translation
        text_to_translate = st.text_area("Enter Text to Translate:")
        client = st.session_state.openai_api_client
        
        if text_to_translate != "" and st.button("Translate"):
            with st.spinner("Translating... This may take a while."):
                translated_text = translate(client, text_to_translate, model=st.session_state.model_translate, 
                                            input_lang=st.session_state.source_lang_translate, 
                                            target_lang=st.session_state.target_lang_translate,
                                            temperature=st.session_state.temperature,
                                            top_p=st.session_state.top_p)
                st.markdown(translated_text)
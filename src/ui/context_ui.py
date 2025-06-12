import streamlit as st
import pysubs2
import os
import tempfile
import sys
sys.path.append('../')

from src.logic.context import *

def tab_context():
    st.header("Generate Context Data")
    
    # Keyowrds to use when doing web context search
    st.subheader("Web Context Input")
    
    left, right = st.columns(2)
    
    with left:
        series_name = st.text_input("Series Name", value=st.session_state.get("series_name", ""), help="Series name to use in automated web search.")
    
    with right:
        keywords = st.text_input("Keywords", value=st.session_state.get("keywords", ""), help="Keywords to include in automated web search.")

    # Loading Subtitile Files
    st.subheader("Subtitle File")
    uploaded_file = st.file_uploader("Upload a subtitle file", type=["srt", "ass"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
            
        subs = pysubs2.load(tmp_path, encoding="utf-8")
        transcript = "\n".join([line.text for line in subs])
        os.remove(tmp_path)
    else:
        return
    
    # Chosing which context functions to use
    st.subheader("Select Context Functions to Run")      
    selected_context_tasks = st.multiselect(
        "Select Context Functions to Run",
        options=[
            "Automated Web Search",
            "Generate Character List",
            "High Level Synopsis"
        ],
        default=[
            "Automated Web Search",
            "Generate Character List",
            "High Level Synopsis"
        ],
    )
    
    if st.button("Run Selected Functions", use_container_width=True):
        # Temp references to session state
        input_lang = st.session_state.get("input_lang", "ja")
        output_lang = st.session_state.get("output_lang", "en")
        model = st.session_state.get("gpt_instance", None)
        search_tool = st.session_state.get("web_search_instance")
        
        synopsis = st.session_state.get("synopsis", "")
        series_name = st.session_state.get("series_name", "")
        keywords = st.session_state.get("keywords", "")
        character_list = st.session_state.get("character_list", "")
        web_context = st.session_state.get("web_context", "")

        if not model:
            st.error("ChatGPT model is not loaded.")
            return

        if "Automated Web Search" in selected_context_tasks:
            if not search_tool:
                st.error("Tavily web search tool is not loaded.")
                return
            with st.spinner("Gathering web context..."):
                web_context = generate_web_context(model, search_tool, series_name=series_name, keywords=keywords,
                                                   input_lang=input_lang, output_lang=output_lang)
                st.session_state["web_context"] = web_context
        
        if "Generate Character List" in selected_context_tasks:
            with st.spinner("Generating Character List..."):
                character_list = generate_character_list(model, input_lang, output_lang, transcript, web_context)
                st.session_state["character_list"] = character_list
        
        if "High Level Synopsis" in selected_context_tasks:
            with st.spinner("Generating Synopsis..."):
                synopsis = generate_high_level_summary(model, input_lang, output_lang, transcript, character_list)
                st.session_state["synopsis"] = synopsis


        st.success("Selected context functions completed.")

    # Let the user update the context fields on their own
    st.subheader("Edit Context")
    st.session_state["web_context"] = st.text_area(
        "Web Search Results",
        value=st.session_state.get("web_context", ""),
        height=120,
    )
    
    st.session_state["character_list"] = st.text_area(
        "Character List",
        value=st.session_state.get("character_list", ""),
        height=120,
    )

    st.session_state["synopsis"] = st.text_area(
        "High Level Synopsis",
        value=st.session_state.get("synopsis", ""),
        height=150,
    )

    # Save to session_state
    st.session_state["series_name"] = series_name
    st.session_state["keywords"] = keywords
        
        
    
    
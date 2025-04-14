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
    series_name = st.text_input("Series Name", value=st.session_state.get("series_name", ""), help="for web context")
    keywords = st.text_input("Search Keywords", value=st.session_state.get("web_keywords", ""), help="e.g., character names, setting, terms")

    # Loading Subtitile Files
    st.subheader("Subtitle File")
    uploaded_file = st.file_uploader("Upload a subtitle file", type=["srt", "ass"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
            
        subs = pysubs2.load(tmp_path, encoding="utf-8")
        full_text = "\n".join([line.text for line in subs])
        os.remove(tmp_path)
    
    # Chosing which context functions to use
    st.subheader("Select Context Functions to Run")      
    selected_context_tasks = st.multiselect(
        "Select Context Functions to Run",
        options=[
            "Scene Structure",
            "Web Context",
            "Characters",
            "Synopsis",
            "Tone"
        ],
        default=[
            "Scene Structure",
            "Web Context",
            "Characters",
            "Synopsis",
            "Tone"
        ],
    )
    
    if st.button("Run Selected Functions", use_container_width=True):
        # Temp references to session state
        input_lang = st.session_state.get("input_lang", "ja")
        output_lang = st.session_state.get("output_lang", "en")
        format_description = st.session_state.get("format_description", None)
        characters = st.session_state.get("context_characters", None)
        series_name = st.session_state.get("series_name", None)
        web_keywords = st.session_state.get("web_keywords", None)
        model = st.session_state.get("gpt_instance", None)
        search_tool = st.session_state.get("web_search_instance")

        if not model:
            st.error("ChatGPT model is not loaded.")
            return

        web_context = ""
        
        if "Scene Structure" in selected_context_tasks:
            with st.spinner("Determining scene structure..."):
                st.session_state["context_scene_structure"] = determine_scene_structure(model, input_lang, output_lang, full_text)

        if "Web Context" in selected_context_tasks:
            if not search_tool:
                st.error("Tavily web search tool is not loaded.")
                return
            with st.spinner("Gathering web context..."):
                web_context = gather_context_from_web(model, search_tool, output_lang, series_name, web_keywords)
                st.session_state["context_web_summary"] = web_context

        if "Characters" in selected_context_tasks:
            with st.spinner("Identifying characters..."):
                characters = identify_characters(model, input_lang, output_lang, full_text, format_description, web_context)
                st.session_state["context_characters"] = characters

        if "Synopsis" in selected_context_tasks:
            with st.spinner("Summarizing scene..."):
                st.session_state["context_scene_summary"] = summarize_scene(model, input_lang, output_lang, 
                                                                            full_text, format_description, characters, web_context)

        if "Tone" in selected_context_tasks:
            with st.spinner("Analyzing tone and formality..."):
                st.session_state["context_tone"] = determine_tone(model, input_lang, output_lang,
                                                                  full_text, format_description, web_context)

        st.success("Selected context functions completed.")

    # Let the user update the context fields on their own
    st.subheader("Edit Context")   
    st.session_state["context_scene_structure"] = st.text_area(
        "Scene Structure",
        value=st.session_state.get("context_scene_structure", ""),
        height=120,
    )

    st.session_state["context_web_summary"] = st.text_area(
        "Web Context Summary",
        value=st.session_state.get("context_web_summary", ""),
        height=150,
    )

    st.session_state["context_characters"] = st.text_area(
        "Character List",
        value=st.session_state.get("context_characters", ""),
        height=150,
    )

    st.session_state["context_scene_summary"] = st.text_area(
        "Scene Synopsis",
        value=st.session_state.get("context_scene_summary", ""),
        height=150,
    )

    st.session_state["context_tone"] = st.text_area(
        "Tone and Style",
        value=st.session_state.get("context_tone", ""),
        height=100,
    )
    
    # Save to session_state
    st.session_state["series_name"] = series_name
    st.session_state["web_keywords"] = keywords
        
        
    
    
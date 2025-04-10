import streamlit as st
from src.context import summarize, identify_characters, determine_tone, analyze_format
import pysubs2
import tempfile
import os

def render_context():
    st.header("Context")

    uploaded_file = st.file_uploader("Upload Subtitle File (.srt or .ass)", type=["srt", "ass"])
    
    autofill_options = st.multiselect(
        "Which parts would you like to autofill?",
        options=["Scene Summary", "Characters", "Tone", "Format"],
        default=["Scene Summary", "Characters", "Tone", "Format"]
    )
    
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
            
        subs = pysubs2.load(tmp_path, encoding="utf-8")
        full_text = "\n".join([line.text for line in subs])

        if st.session_state.openai_api_client is None:
            st.error("OpenAI API client not loaded. Please load it in the Configurations page.")
        else:
            if st.button("Analyze"):
                with st.spinner("Analyzing context..."):
                    client = st.session_state.openai_api_client
                    if not client:
                        st.error("OpenAI client not initialized. Please load it in the Config tab.")
                    else:
                        format_desc = None
                        char_output = None

                        if "Format" in autofill_options:
                            format_desc = analyze_format(client, full_text)
                            st.session_state.context_story_format = format_desc
                        else:
                            format_desc = st.session_state.context_story_format  # fallback

                        if "Characters" in autofill_options:
                            char_output = identify_characters(client, full_text, format_description=format_desc)
                            st.session_state.context_characters = char_output
                        else:
                            char_output = st.session_state.context_characters  # fallback

                        if "Scene Summary" in autofill_options:
                            st.session_state.context_scene_backstory = summarize(client, full_text,
                                                                                 format_description=format_desc, 
                                                                                 character_list=char_output)

                        if "Tone" in autofill_options:
                            st.session_state.context_tone = determine_tone(client, full_text, format_description=format_desc)

                        st.rerun()
    
    # Editable fields (populated or blank)
    st.markdown("#### Format")
    st.text_area(
        label="Format",
        placeholder="Describe the structure: is it monologue, conversation, or mixed?",
        key="context_story_format",
        height=150,
        label_visibility="collapsed"
    )
    
    st.markdown("#### Characters")
    st.text_area(
        label="Characters",
        placeholder="List character names, their roles, and relevant traits (e.g. flirty, formal, boss, sibling...)",
        key="context_characters",
        height=150,
        label_visibility="collapsed"
    )

    st.markdown("#### Scene Summary")
    st.text_area(
        label="Scene Summary",
        placeholder="Write or revise a neutral summary of the scene's events (what happens, who talks, etc.)",
        key="context_scene_backstory",
        height=200,
        label_visibility="collapsed"
    )

    st.markdown("#### Tone")
    st.text_area(
        label="Tone",
        placeholder="Describe the tone: speech level, mood shifts, formality, emotional undercurrents...",
        key="context_tone",
        height=150,
        label_visibility="collapsed"
)

def get_context_dict():
    """
    Return a dictionary of context variables.
    """
    context = {}

    context["Format"] = st.session_state.get("context_story_format").strip() or "No format description provided."
    context["Characters"] = st.session_state.get("context_characters").strip() or "No characters provided."
    context["Scene Summary"] = st.session_state.get("context_scene_backstory").strip() or "No scene summary provided."
    context["Tone"] = st.session_state.get("context_tone").strip() or "No tone provided."

    return context


def render_context_dict(context_dict):
    """
    Render the context dictionary in a readable format.
    """
    for section, content in context_dict.items():
        with st.expander(section, expanded=False):
            st.markdown(f"""
            <div style='
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 0.75rem;
                margin-bottom: 0.75rem;
            '>
                <strong>{section}</strong><br>
                <div style='white-space: pre-wrap; font-family: monospace;'>{content}</div>
            </div>
            """, unsafe_allow_html=True)

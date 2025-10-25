import streamlit as st
import sys
import tempfile
import os
import pysubs2
sys.path.append('../')

from src.backend.business.translate import translate_multi_response, translate_subs
from src.frontend.shared_ui import show_context, get_context_dict
from src.backend.utils import load_sub_data

def tab_translate():
    st.header("Translate")
    
    show_context("translate_line")
        
    st.subheader("Input")
    input_text = st.text_area("Text to Translate", value=st.session_state.get("raw_input_text", ""))
    st.session_state["raw_input_text"] = input_text
    
    if st.session_state["gpt_instance"] is None:
        st.error("Please load a the OpenAI API to use this functionality.")
        return
    
    if st.button("Translate", use_container_width=True, type="primary"):
        llm = st.session_state.get("gpt_instance")

        if not llm:
            st.error("OpenAI model is not loaded.")
        elif not input_text.strip():
            st.warning("Please enter some text to translate.")
        else:
            with st.spinner("Translating...", show_time=True):
                translation = translate_multi_response(
                    llm=llm,
                    text=input_text,
                    context=get_context_dict(),
                    input_lang=st.session_state.get("input_lang", "ja"),
                    target_lang=st.session_state.get("output_lang", "en")
                )

                st.session_state["translated_output"] = translation
                
    translation = st.session_state.get("translated_output", "")
    render_translated_text(translation)
                
def render_translated_text(translated_text):
    if translated_text == "":
        return

    # Basic markdown parsing
    parts = {
        "Naturalized Translation": "",
        "Annotated Translation": ""
    }
    current = None
    for line in translated_text.splitlines():
        if "Naturalized Translation" in line:
            current = "Naturalized Translation"
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


def tab_translate_file():
    st.header("Translate File")
    
    st.warning(
        "Subtitle file translation will use your OpenAI tokens **for every line**, "
        "which can get expensive for longer files.\n\n"
        "To reduce cost, consider translating only selected lines or breaking the file into smaller chunks."
    )
    
    show_context("translate_file")
    
    st.subheader("Translation")
    
    # Step 1: Load from session if previously uploaded
    uploaded_file = st.file_uploader("Upload a subtitle file", type=["srt", "ass"], key="subtitle_uploader_translate")
    
    if st.session_state["gpt_instance"] is None:
        st.error("Please load a the OpenAI API to use this functionality.")
        return
    
    file_name = "default.ass"
    
    if uploaded_file:
        file_name = uploaded_file.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        try:
            subs = pysubs2.load(tmp_path, encoding="utf-8")
            sub_data = load_sub_data(tmp_path, include_speaker=False)
            disable_button = False
            
            with st.expander("Stats"):
                total_lines = len(sub_data)
                total_chars = sum(len(line) for line in sub_data)
                avg_chars_per_line = total_chars / total_lines if total_lines > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Lines", f"{total_lines:,}")
                with col2:
                    st.metric("Total Characters", f"{total_chars:,}")
                with col3:
                    st.metric("Average Characters Per Line", f"{avg_chars_per_line:,.2f}")
            
            with st.expander("Preview"):
                st.write(sub_data[:10])
        except:
            st.error("Failed to read subtitle file. Please try reuploading it.")
            disable_button = True
    else:
        disable_button = True
        
    context_window = st.number_input("Context Window", min_value=1, max_value=5, help="The number of lines before and after the current line to look at while translating", value=3)
    st.session_state["context_window"] = context_window
        
    if st.button("Translate File", key="translate_sub_file_button", type="primary",
                 use_container_width=True, disabled=disable_button):
        llm = st.session_state.get("gpt_instance")
        if not llm:
            st.error("OpenAI model is not loaded.")
        else:
            with st.spinner("Translating File...", show_time=True):
                translate_subs(llm, subs, context_window=context_window,
                               input_lang=st.session_state.get("input_lang", "ja"),
                               target_lang=st.session_state.get("output_lang", "en"),
                               context=get_context_dict()
                )
                st.session_state["translated_subtitle_file"] = subs
                st.success("Translation Complete")
    
    # Get the generated sub file if it was created
    transcript_file = st.session_state.get("translated_subtitle_file", None)
    if isinstance(transcript_file, pysubs2.SSAFile):
        st.subheader("File Download")
        
        # Save the subtitle to a temp .ass file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ass") as temp_sub_file:
            transcript_file.save(temp_sub_file.name)
            sub_file_path = temp_sub_file.name
            
            subs = pysubs2.load(sub_file_path, encoding="utf-8")
            sub_data = load_sub_data(sub_file_path, include_speaker=False)
            with st.expander("Preview"):
                st.write(sub_data[:10])
            
        # Make it downloadable
        with open(sub_file_path, "rb") as f:
            st.download_button(
                label="Download .ass Subtitle File",
                data=f.read(),
                file_name=file_name.rsplit(".", 1)[0] + ".ass",
                mime="text/plain",
                use_container_width=True,
                type="primary"
            )


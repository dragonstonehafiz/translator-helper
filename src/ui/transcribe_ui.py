import streamlit as st
import tempfile
import os
import pysubs2
from src.logic.transcribe import transcribe_line, transcribe_file

def tab_transcribe_line():
    """
    Transcribes audio as a single line of text.
    """
    st.header("Transcribe")

    if st.session_state.whisper_instance is None:
        st.error("Whisper model not loaded. Please load it in the Configurations page.")
        return

    # Mode switcher: Mic or File
    mode = st.radio("Select Audio Input Mode", ["Microphone", "Upload File"], horizontal=True)

    audio_data = None
    file_name = None

    if mode == "Microphone":
        audio_data = st.audio_input("Record from mic")
        file_name = "mic_input.wav"
    else:
        uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav"])
        if uploaded_file:
            st.audio(uploaded_file)
            audio_data = uploaded_file
            file_name = uploaded_file.name

    if audio_data:
        if st.button("Transcribe", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[-1]) as temp_audio:
                temp_audio.write(audio_data.read())
                temp_audio_path = temp_audio.name

            with st.spinner("Transcribing..."):
                transcript = transcribe_line(
                    st.session_state.whisper_instance,
                    temp_audio_path,
                    st.session_state.input_lang
                )
                st.code(transcript, language='plaintext')

        
def tab_transcribe_file():
    """
    Transcribes audio and generates an ass file from it.
    """
    st.header("Transcribe File")
    
    audio_data = None
    file_name = "default.ass"
    
    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav"])
    if uploaded_file:
        st.audio(uploaded_file)
        audio_data = uploaded_file
        file_name = uploaded_file.name
        
    if audio_data:
        if st.button("Transcribe", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[-1]) as temp_audio:
                temp_audio.write(audio_data.read())
                temp_audio_path = temp_audio.name
            
            
            with st.spinner("Transcribing..."):
                subs = transcribe_file(
                    st.session_state.whisper_instance,
                    temp_audio_path,
                    st.session_state.input_lang
                )
                
                st.session_state["transcript_file"] = subs
                st.success("Transcription complete. Scroll down to download the .ass file.")
                
                
    # Get the generated sub file if it was created
    transcript_file = st.session_state.get("transcript_file", None)
    if type(transcript_file) == pysubs2.SSAFile and file_name is not None:
        # Save the subtitle to a temp .ass file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ass") as temp_sub_file:
            transcript_file.save(temp_sub_file.name)
            sub_file_path = temp_sub_file.name
            
        # Make it downloadable
        with open(sub_file_path, "rb") as f:
            st.download_button(
                label="Download .ass Subtitle File",
                data=f.read(),
                file_name=file_name.rsplit(".", 1)[0] + ".ass",
                mime="text/plain",
                use_container_width=True
            )
        
    
    


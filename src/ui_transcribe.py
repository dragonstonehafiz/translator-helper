import streamlit as st
import tempfile
import os
import time
from src.transcribe import transcribe
        
def create_temp_audio_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return temp_file.name

def render_transcribe():
    st.header("Transcribe")
    
    if st.session_state.whisper_model is None:
        st.error("Whisper model not loaded. Please load it in the Configurations page.")
    else:
        uploaded_file = st.file_uploader("Choose a file", type=["mp3", "wav"])
        # Audio Preview
        if uploaded_file:
            st.audio(uploaded_file)
        
        # Transcription Button
        if uploaded_file and st.button("Transcribe"):
            startTime = time.time()
            with st.spinner("Transcribing... This may take a while."):
                file_path = create_temp_audio_file(uploaded_file)
                transcript = transcribe(st.session_state.whisper_model, file_path, st.session_state.input_lang)
                endTime = time.time()
                st.write(f"Time Taken: {endTime-startTime:0.2f}s")
                st.code(transcript, language='plaintext')
            
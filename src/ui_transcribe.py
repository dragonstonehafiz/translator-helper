import streamlit as st
import whisper
import tempfile
import os
import time

from src.transcribe import transcribe

def load_whisper_model(selected_model: str = None): 
    if selected_model is not None:
        st.session_state.selected_model_transcribe = selected_model
    with st.spinner("Loading Whisper model... This may take a while."):
        st.session_state.whisper_model = whisper.load_model(st.session_state.selected_model_transcribe, device=st.session_state.device)  # Force CPU usage
        
def create_temp_audio_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return temp_file.name

def render_transcribe():
    st.header("Transcribe")
    
    leftcol, rightcol = st.columns(2)
    
    # Model Selection
    with leftcol:
        model_options = ["tiny", "base", "small", "medium", "large"]
        selected_model = st.selectbox("Select Whisper Model:", model_options, 
                                      index=model_options.index(st.session_state.selected_model_transcribe))
        if selected_model != st.session_state.selected_model_transcribe:
            load_whisper_model(selected_model)
    
    # Language Selection
    with rightcol:
        st.session_state.input_lang = st.text_input("Input Language", 
                                                   st.session_state.input_lang)
        
    # File Uploader
    st.subheader("Upload an MP3 or WAV file:")
    uploaded_file = st.file_uploader("Choose a file", type=["mp3", "wav"])
    
    # Transcription Button
    if uploaded_file and st.button("Transcribe"):
        startTime = time.time()
        with st.spinner("Transcribing... This may take a while."):
            file_path = create_temp_audio_file(uploaded_file)
            transcript = transcribe(st.session_state.whisper_model, file_path, st.session_state.input_lang)
            endTime = time.time()
            st.write(f"Time Taken: {endTime-startTime:0.2f}s")
            st.code(transcript, language='plaintext')
            
import streamlit as st
import tempfile
import os
from src.logic.transcribe import transcribe

def tab_transcribe():
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
                transcript = transcribe(
                    st.session_state.whisper_instance,
                    temp_audio_path,
                    st.session_state.input_lang
                )
                st.code(transcript, language='plaintext')
                


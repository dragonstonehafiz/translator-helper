import io
import os
import tempfile
import wave
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.backend.business.transcribe import transcribe_file, transcribe_line


def _plot_waveform(audio_bytes: bytes, sample_limit: int = 2000) -> None:
    """Render a waveform chart for the provided audio bytes."""
    try:
        with wave.open(io.BytesIO(audio_bytes)) as wav_file:
            sample_width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()
            framerate = wav_file.getframerate()
            frames = wav_file.getnframes()
            raw = wav_file.readframes(frames)
    except wave.Error:
        st.warning("Unable to read audio data for waveform preview.")
        return

    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width)
    if dtype is None:
        st.warning("Unsupported audio format for waveform preview.")
        return

    samples = np.frombuffer(raw, dtype=dtype)
    if sample_width == 1:
        samples = samples.astype(np.int16) - 128

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    if len(samples) == 0:
        st.warning("No audio samples found for waveform preview.")
        return

    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples = samples / max_val

    time_axis = np.linspace(0, len(samples) / framerate, num=len(samples))
    df = pd.DataFrame({"time": time_axis, "amplitude": samples})

    if len(df) > sample_limit:
        step = max(1, len(df) // sample_limit)
        df = df.iloc[::step, :]

    st.line_chart(df.set_index("time"))


def _write_temp_audio(audio_bytes: bytes, suffix: str = ".wav") -> str:
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_file.write(audio_bytes)
    tmp_file.flush()
    tmp_file.close()
    return tmp_file.name


def _transcribe_audio_bytes(audio_bytes: bytes, language: str) -> str:
    model = st.session_state.get("whisper_instance")
    if model is None:
        st.error("Whisper model is not loaded. Please configure it in Settings.")
        return ""

    temp_path = _write_temp_audio(audio_bytes)
    try:
        with st.spinner("Transcribing audio..."):
            return transcribe_line(model, temp_path, language)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _render_soundbite_tab():
    st.subheader("Transcribe Soundbite")
    st.caption("Record a short clip, preview the waveform, then transcribe it.")

    audio_data = st.audio_input("Record from microphone", key="soundbite_input")

    if audio_data is None:
        st.info("Record audio using the widget above to get started.")
        return

    audio_bytes = audio_data.getvalue()
    st.audio(audio_bytes, format="audio/wav")
    _plot_waveform(audio_bytes)

    if st.button("Transcribe Recording", use_container_width=True):
        transcript = _transcribe_audio_bytes(audio_bytes, st.session_state.get("input_lang", "ja"))
        if transcript:
            st.markdown("### Transcript")
            st.code(transcript, language="plaintext")


def _transcribe_file(uploaded_file, output_name: str, output_dir: str) -> None:
    model = st.session_state.get("whisper_instance")
    if model is None:
        st.error("Whisper model is not loaded. Please configure it in Settings.")
        return

    uploaded_file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as temp_audio:
        temp_audio.write(uploaded_file.read())
        temp_audio_path = temp_audio.name

    try:
        with st.spinner("Transcribing file..."):
            subs = transcribe_file(model, temp_audio_path, st.session_state.get("input_lang", "ja"))
    finally:
        try:
            os.remove(temp_audio_path)
        except OSError:
            pass

    if isinstance(subs, str):
        st.error(subs)
        return

    st.success("Transcription complete.")

    preview_lines = [event.text for event in subs.events[:10]]
    st.markdown("### Preview")
    st.write(preview_lines)

    output_dir_path = Path(output_dir).expanduser()
    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_name = output_name.strip() or f"{Path(uploaded_file.name).stem}.{st.session_state.get('input_lang', 'ja')}.ass"
    if not output_name.lower().endswith(".ass"):
        output_name += ".ass"
    output_path = output_dir_path / output_name
    subs.save(str(output_path))

    with open(output_path, "rb") as f:
        st.download_button(
            label="Download .ass Subtitle File",
            data=f.read(),
            file_name=output_path.name,
            mime="text/plain",
            use_container_width=True,
        )

    st.info(f"Saved transcription to {output_path.resolve()}")


def _render_file_tab():
    st.subheader("Transcribe File")
    st.caption("Upload an audio file and receive a subtitle file in .ass format.")

    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a"], key="transcribe_file_uploader")

    if uploaded_file is None:
        st.info("Upload an audio file to begin transcription.")
        return

    file_bytes = uploaded_file.getvalue()
    st.audio(file_bytes, format="audio/wav")
    _plot_waveform(file_bytes)

    default_output_name = f"{Path(uploaded_file.name).stem}.{st.session_state.get('input_lang', 'ja')}.ass"
    if (
        "transcribe_output_filename" not in st.session_state
        or st.session_state.get("transcribe_last_upload") != uploaded_file.name
    ):
        st.session_state["transcribe_output_filename"] = default_output_name
        st.session_state["transcribe_last_upload"] = uploaded_file.name

    output_dir = Path("output")
    absolute_output_dir = output_dir.absolute().resolve()

    st.text_input(
        "Output File Name",
        key="transcribe_output_filename",
    )
    st.markdown("Output Directory:")
    st.code(str(absolute_output_dir))

    if st.button("Transcribe File", use_container_width=True):
        uploaded_file.seek(0)
        _transcribe_file(
            uploaded_file,
            st.session_state["transcribe_output_filename"],
            str(output_dir),
        )


def render_transcribe_page() -> None:
    soundbite_tab, file_tab = st.tabs(["Transcribe Soundbite", "Transcribe File"])

    with soundbite_tab:
        _render_soundbite_tab()

    with file_tab:
        _render_file_tab()


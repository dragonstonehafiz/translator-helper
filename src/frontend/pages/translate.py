import os
import tempfile
from pathlib import Path

import pysubs2
import streamlit as st

from src.backend.business.translate import (
    translate_multi_response,
    translate_subs,
)
from src.backend.utils import load_sub_data


def _context_section() -> dict:
    st.subheader("Context Inputs")

    if "include_web_context" not in st.session_state:
        st.session_state["include_web_context"] = True
    if "include_character_list" not in st.session_state:
        st.session_state["include_character_list"] = True
    if "include_synopsis" not in st.session_state:
        st.session_state["include_synopsis"] = True

    context_payload = {}

    def context_block(label: str, key: str, checkbox_key: str):
        col_check, col_content = st.columns([1, 10])
        with col_check:
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = True
            st.checkbox(
                f"Include",
                key=checkbox_key,
            )
        with col_content:
            with st.expander(label, expanded=True):
                st.text_area(
                    label,
                    key=key,
                    height=180,
                )
        if st.session_state[checkbox_key]:
            context_payload[label] = st.session_state.get(key, "")

    context_block("Web Context", "web_context", "include_web_context")
    context_block("Character List", "character_list", "include_character_list")
    context_block("High Level Summary", "synopsis", "include_synopsis")

    return context_payload


def _render_line_translation(context_payload: dict) -> None:
    st.subheader("Translate Line")

    input_text = st.text_area(
        "Source Text",
        key="translate_line_input",
        height=200,
        placeholder="Paste or type the text you want to translate.",
    )

    if st.button("Translate Text", key="translate_line_button", use_container_width=True):
        llm = st.session_state.get("gpt_instance")
        if not llm:
            st.error("OpenAI model is not loaded. Please configure it in Settings.")
            return

        if not input_text.strip():
            st.warning("Enter some text to translate.")
            return

        with st.spinner("Translating line..."):
            translation = translate_multi_response(
                llm=llm,
                text=input_text,
                context=context_payload,
                input_lang=st.session_state.get("input_lang", "ja"),
                target_lang=st.session_state.get("output_lang", "en"),
            )
            st.session_state["translate_line_result"] = translation

    output = st.session_state.get("translate_line_result", "")
    if output:
        st.markdown("### Translation Output")
        st.markdown(output)


def _render_file_translation(context_payload: dict) -> None:
    st.subheader("Translate Subtitle File")

    uploaded_file = st.file_uploader(
        "Upload subtitle file",
        type=["ass", "srt"],
        key="translate_file_uploader",
    )

    context_window = st.number_input(
        "Context Window (number of surrounding lines)",
        min_value=1,
        max_value=5,
        value=st.session_state.get("translate_context_window", 3),
        key="translate_context_window",
    )

    if uploaded_file:
        try:
            uploaded_path = Path(uploaded_file.name)
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_path.suffix) as tmp_file:
                tmp_file.write(uploaded_file.read())
                temp_path = tmp_file.name

            subs = pysubs2.load(temp_path, encoding="utf-8")
            sub_data = load_sub_data(temp_path, include_speaker=False)

            total_lines = len(sub_data)
            total_chars = sum(len(line) for line in sub_data)
            avg_chars = total_chars / total_lines if total_lines else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Lines", f"{total_lines:,}")
            col2.metric("Total Characters", f"{total_chars:,}")
            col3.metric("Characters / Line", f"{avg_chars:,.2f}")

            st.markdown("#### Preview")
            st.write(sub_data[:10])

        except Exception as exc:
            st.error(f"Failed to read subtitle file: {exc}")
            subs = None
            uploaded_path = None
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
    else:
        subs = None
        uploaded_path = None

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    absolute_output_dir = output_dir.resolve()

    if uploaded_path:
        default_name = f"{uploaded_path.stem}.{st.session_state.get('output_lang', 'en')}.ass"
        if st.session_state.get("translate_last_upload") != uploaded_path.name:
            st.session_state["translate_output_filename"] = default_name
            st.session_state["translate_last_upload"] = uploaded_path.name
    elif "translate_output_filename" not in st.session_state:
        st.session_state["translate_output_filename"] = "translated.ass"

    st.text_input(
        "Output File Name",
        key="translate_output_filename",
    )
    st.markdown("Output Directory:")
    st.code(str(absolute_output_dir))

    if st.button("Translate File", key="translate_file_button", use_container_width=True):
        llm = st.session_state.get("gpt_instance")
        if not llm:
            st.error("OpenAI model is not loaded. Please configure it in Settings.")
            return
        if not uploaded_file or subs is None:
            st.error("Upload a valid subtitle file first.")
            return

        with st.spinner("Translating subtitle file..."):
            translated_subs = translate_subs(
                llm=llm,
                subs=subs,
                context=context_payload,
                context_window=context_window,
                input_lang=st.session_state.get("input_lang", "ja"),
                target_lang=st.session_state.get("output_lang", "en"),
            )
            st.session_state["translated_subs"] = translated_subs
            st.session_state["translated_subs_source_name"] = uploaded_path.stem if uploaded_path else "translated"
            st.success("Subtitle translation complete.")

    translated = st.session_state.get("translated_subs")
    if isinstance(translated, pysubs2.SSAFile):
        output_name = st.session_state.get("translate_output_filename", "translated.ass")
        if not output_name.lower().endswith(".ass"):
            output_name += ".ass"
        output_path: Path = absolute_output_dir / output_name

        translated.save(str(output_path))
        st.info(f"Saved translated file to {output_path.absolute()}")

        with open(output_path, "rb") as fp:
            st.download_button(
                label="Download Translated Subtitles",
                data=fp.read(),
                file_name=output_path.name,
                mime="text/plain",
                use_container_width=True,
            )
    else:
        subs = None


def render_translate_page() -> None:
    st.title("Translate")
    st.caption("Use the context above to drive high-quality translations.")

    context_payload = _context_section()

    tab_line, tab_file = st.tabs(["Translate Line", "Translate File"])

    with tab_line:
        _render_line_translation(context_payload)

    with tab_file:
        _render_file_translation(context_payload)

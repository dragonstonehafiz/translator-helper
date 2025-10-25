import json
import tempfile
from pathlib import Path

import streamlit as st

from src.backend.business.context import (
    generate_character_list,
    generate_high_level_summary,
    generate_web_context,
)
from src.backend.utils import load_sub_data

CONTEXT_DIR = Path("context")
CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def _load_transcript_from_file(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".ass", ".srt"}:
        st.error("Unsupported file type. Please upload a .ass or .srt file.")
        return ""

    tmp_dir = Path(tempfile.gettempdir()) / "translator_helper_context"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = tmp_dir / uploaded_file.name

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    try:
        lines = load_sub_data(str(temp_path), include_speaker=True)
        return "\n".join(lines)
    finally:
        temp_path.unlink(missing_ok=True)


def _run_context_workflow(
    selected_tasks,
    transcript: str,
    model,
    search_tool,
    input_lang,
    output_lang,
    series_name,
    keywords,
):
    execution_order = [
        "Automated Web Search",
        "Generate Character List",
        "High Level Summary",
    ]

    web_context = st.session_state.get("web_context", "")
    character_list = st.session_state.get("character_list", "")
    synopsis = st.session_state.get("synopsis", "")

    for task in execution_order:
        if task not in selected_tasks:
            continue

        if task == "Automated Web Search":
            if not search_tool:
                st.error("Tavily search is not configured.")
                return
            with st.spinner("Generating web context..."):
                web_context = generate_web_context(
                    model,
                    search_tool,
                    input_lang=input_lang,
                    output_lang=output_lang,
                    series_name=series_name,
                    keywords=keywords,
                )
                st.session_state["web_context"] = web_context

        elif task == "Generate Character List":
            if not transcript:
                st.error("Transcript is required to generate a character list.")
                return
            with st.spinner("Generating character list..."):
                character_list = generate_character_list(
                    model,
                    input_lang=input_lang,
                    output_lang=output_lang,
                    transcript=transcript,
                    web_context=web_context,
                )
                st.session_state["character_list"] = character_list

        elif task == "High Level Summary":
            if not transcript:
                st.error("Transcript is required to generate a summary.")
                return
            with st.spinner("Generating high level summary..."):
                synopsis = generate_high_level_summary(
                    model,
                    input_lang=input_lang,
                    output_lang=output_lang,
                    transcript=transcript,
                    character_list=character_list,
                )
                st.session_state["synopsis"] = synopsis


def _save_context_to_file(filename: str) -> None:
    if not filename:
        st.error("Please provide a filename to save the context.")
        return

    if not filename.lower().endswith(".json"):
        filename += ".json"

    payload = {
        "series_name": st.session_state.get("series_name", ""),
        "keywords": st.session_state.get("keywords", ""),
        "web_context": st.session_state.get("web_context", ""),
        "character_list": st.session_state.get("character_list", ""),
        "synopsis": st.session_state.get("synopsis", ""),
    }

    target_path = CONTEXT_DIR / filename
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    st.success(f"Context saved to {target_path.resolve()}")


def _load_context_from_file(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        st.error(f"Failed to load context: {exc}")
        return

    for key in ("series_name", "keywords", "web_context", "character_list", "synopsis"):
        if key in st.session_state:
            del st.session_state[key]

    st.session_state["series_name"] = data.get("series_name", "")
    st.session_state["keywords"] = data.get("keywords", "")
    st.session_state["web_context"] = data.get("web_context", "")
    st.session_state["character_list"] = data.get("character_list", "")
    st.session_state["synopsis"] = data.get("synopsis", "")
    st.success(f"Loaded context from {path}")


def render_context_page() -> None:
    st.title("Context")
    st.caption("Manage scene context details and run helper workflows.")

    tabs = st.tabs(["Generate from Subtitle", "Load / Save Context"])

    with tabs[0]:
        st.subheader("Generate Context from Subtitle")

        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Series Name",
                key="series_name",
            )
        with col2:
            st.text_input(
                "Keywords",
                key="keywords",
            )

        uploaded_file = st.file_uploader(
            "Upload Transcript (.ass or .srt)",
            type=["ass", "srt"],
            key="context_transcript",
        )

        options = [
            "Automated Web Search",
            "Generate Character List",
            "High Level Summary",
        ]
        selected_options = st.multiselect(
            "Select context functions to run",
            options=options,
            default=options,
            key="context_selected_options",
        )

        if st.button("Run Selected Functions", use_container_width=True):
            input_lang = st.session_state.get("input_lang", "ja")
            output_lang = st.session_state.get("output_lang", "en")
            model = st.session_state.get("gpt_instance")
            search_tool = st.session_state.get("web_search_instance")

            if not model:
                st.error("OpenAI model is not loaded. Please configure it in Settings.")
            else:
                transcript = ""
                if uploaded_file:
                    transcript = _load_transcript_from_file(uploaded_file)
                elif any(
                    task in selected_options for task in ("Generate Character List", "High Level Summary")
                ):
                    st.error("Transcript file required for selected functions.")
                    return

                _run_context_workflow(
                    selected_options,
                    transcript,
                    model,
                    search_tool,
                    input_lang,
                    output_lang,
                    st.session_state.get("series_name", ""),
                    st.session_state.get("keywords", ""),
                )

    with tabs[1]:
        st.subheader("Load or Save Context Snapshot")

        if not st.session_state.get("context_save_filename"):
            st.session_state["context_save_filename"] = "context_snapshot.json"

        col1, col2 = st.columns([2, 1])
        with col1:
            st.text_input(
                "Save As",
                key="context_save_filename",
                placeholder="context_snapshot.json",
            )
        with col2:
            if st.button("Save Context", use_container_width=True):
                _save_context_to_file(st.session_state.get("context_save_filename", ""))

        saved_files = sorted(CONTEXT_DIR.glob("*.json"))
        st.markdown("### Saved Context Files")
        if not saved_files:
            st.info("No saved context snapshots found.")
        else:
            file_options = {str(path): path for path in saved_files}
            selected_path_str = st.selectbox(
                "Available Snapshots",
                options=list(file_options.keys()),
                key="context_snapshot_select",
            )
            selected_path = file_options[selected_path_str]
            if st.button("Load Selected Context", use_container_width=True):
                _load_context_from_file(selected_path)

    st.subheader("Web Context")
    st.text_area(
        "Web Context",
        key="web_context",
        height=200,
    )

    st.subheader("Character List")
    st.text_area(
        "Character List",
        key="character_list",
        height=200,
    )

    st.subheader("High Level Summary")
    st.text_area(
        "High Level Summary",
        key="synopsis",
        height=200,
    )

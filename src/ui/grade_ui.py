import streamlit as st
import sys
sys.path.append('../')

from src.logic.grade import grade
from src.ui.shared_ui import show_context, get_context_dict
from html import escape

def tab_grade():
    st.subheader("Context")
    
    show_context()
        
    st.subheader("Input")
    
    original_text = st.text_area("Original Text", key="grade_original")
    translated_text = st.text_area("Translated Text", key="grade_translated")
    
    if st.session_state["gpt_instance"] is None:
        st.error("Please load a the OpenAI API to use this functionality.")
        return
    
    if st.button("Grade Translation", use_container_width=True, type="primary"):
        if not original_text.strip() or not translated_text.strip():
            st.warning("Please provide both the original and translated text.")
            return

        with st.spinner("Evaluating translation...", show_time=True):
            output = grade(
                llm=st.session_state["gpt_instance"],  # assumes you've already initialized an LLM in session
                original_text=original_text,
                translated_text=translated_text,
                context=get_context_dict(),
                input_lang=st.session_state.get("input_lang", "ja"),
                target_lang=st.session_state.get("output_lang", "en")
            )
            
            st.session_state["grade_output"] = output
            
    grade_output = st.session_state.get("grade_output", "")
    render_grading_result(grade_output)
            

def render_grading_result(grading_result):
    st.subheader("Translation Evaluation")

    # Parse result
    lines = grading_result.splitlines()
    scores = {}
    suggestions = []
    issues = []
    avg_score = None
    mode = None

    for line in lines:
        if "**Average Score**" in line:
            avg_score = line.split(":")[1].strip()
        elif "**Accuracy**" in line:
            scores['Accuracy'] = line.split("**Accuracy**:")[1].strip()
        elif "**Fluency**" in line:
            scores['Fluency'] = line.split("**Fluency**:")[1].strip()
        elif "**Cultural Appropriateness**" in line:
            scores['Cultural Appropriateness'] = line.split("**Cultural Appropriateness**:")[1].strip()
        elif "**Suggestions for Improvement**" in line:
            mode = "suggest"
        elif "**Notable Issues**" in line:
            mode = "issues"
        elif line.startswith("- ") and mode == "suggest":
            suggestions.append(escape(line[2:].strip()))
        elif line.startswith("- ") and mode == "issues":
            issues.append(escape(line[2:].strip()))

    # Evaluation Summary
    st.markdown(f"""
    <div style='
        background-color: #f9f9f9;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 1rem;
    '>
        <h4 style='margin: 0 0 0.5rem;'>Average Score: {avg_score}</h4>
        <ul style='margin: 0; padding-left: 1.2rem;'>
            <li><strong>Accuracy</strong>: {scores.get('Accuracy', '')}</li>
            <li><strong>Fluency</strong>: {scores.get('Fluency', '')}</li>
            <li><strong>Cultural Appropriateness</strong>: {scores.get('Cultural Appropriateness', '')}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Suggestions Section
    if suggestions:
        st.markdown("#### Suggestions for Improvement")
        for tip in suggestions:
            st.markdown(f"- {tip}")

    # Issues Section
    if issues:
        st.markdown("#### Notable Issues")
        for item in issues:
            st.markdown(f"- {item}")

    
import streamlit as st
from src.translate import grade
from src.ui_context import get_context_dict, render_context_dict
from html import escape

def render_grade():
    st.header("Grade")

    if st.session_state.openai_api_client is None:
        st.error("OpenAI API client not loaded. Please load it in the Configurations page.")
    else:
        # Context Section
        st.subheader("Context")
        context_dict = get_context_dict()
        render_context_dict(context_dict)

        st.subheader("Input")
        # Text Inputs
        original_text = st.text_area("Enter Original Text:")
        translated_text = st.text_area("Enter Translated Text:")
        client = st.session_state.openai_api_client
        # Grade Button
        if st.button("Grade Translation"):
            if not original_text.strip() or not translated_text.strip():
                st.error("Both fields must be filled in before grading.")
            else:
                with st.spinner("Grading translation... This may take a while."):
                    grading_result = grade(client, original_text, translated_text,
                                            model=st.session_state.model_translate,
                                            input_lang=st.session_state.source_lang_translate,
                                            target_lang=st.session_state.target_lang_translate,
                                            temperature=st.session_state.temperature,
                                            top_p=st.session_state.top_p,
                                            context=context_dict)
                    
                    if grading_result:
                        render_grading_result(grading_result)

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


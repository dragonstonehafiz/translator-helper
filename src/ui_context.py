import streamlit as st

def render_context():
    st.header("Context")

    st.text_area(
        "Characters",
        placeholder="List character names, roles, and relationships...",
        key="context_characters",
        height=150
    )

    st.text_area(
        "Scene Backstory",
        placeholder="What's the situation? What's happened recently?",
        key="context_scene_backstory",
        height=150
    )

    st.text_area(
        "Casual Level",
        placeholder='e.g. "Very casual and teasing", "Keigo with some sarcasm", "Formal apology"',
        key="context_casual_level",
        height=100
    )

    st.success("Context will automatically be included in translation and grading prompts.")

def get_context_dict():
    """
    Return a dictionary of context variables.
    """
    context = {}
    if st.session_state.get("context_characters"):
        context["Characters"] = st.session_state.context_characters.strip()
    else:
        context["Characters"] = "No characters provided."
    if st.session_state.get("context_scene_backstory"):
        context["Scene Backstory"] = st.session_state.context_scene_backstory.strip()
    else:
        context["Scene Backstory"] = "No scene backstory provided."
    if st.session_state.get("context_casual_level"):
        context["Casual Level"] = st.session_state.context_casual_level.strip()
    else:
        context["Casual Level"] = "No casual level provided."
    return context


def render_context_dict(context_dict):
    """
    Render the context dictionary in a readable format.
    """
    for section, content in context_dict.items():
        st.markdown(f"""
        <div style='
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
        '>
            <strong>{section}</strong><br>
            <div style='white-space: pre-wrap; font-family: monospace;'>{content}</div>
        </div>
        """, unsafe_allow_html=True)

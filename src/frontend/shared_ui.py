import streamlit as st

def show_context(page_name: str):
    st.subheader("Context")

    def render_item(label, key, default_checked=True):
        col1, col2 = st.columns([6, 1])
        with col1:
            with st.expander(label):
                st.markdown(st.session_state.get(key, f"_No {label.lower()} available._"))
        with col2:
            st.checkbox(f"Include", key=f"include_{key}_{page_name}", value=st.session_state.get(f"include_{key}", default_checked))

    render_item("Web Context", "web_context")
    render_item("Character List", "character_list")
    render_item("Synopsis", "synopsis")
    
        
def get_context_dict():
    context = {}
    if st.session_state.get("include_web_context", True):
        context["web_context"] = st.session_state.get("web_context", "")
    if st.session_state.get("include_character_list", True):
        context["character_list"] = st.session_state.get("character_list", "")
    if st.session_state.get("include_synopsis", True):
        context["high_level_synopsis"] = st.session_state.get("synopsis", "")
        
    return context
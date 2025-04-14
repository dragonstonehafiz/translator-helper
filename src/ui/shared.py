import streamlit as st

def show_context():
    st.subheader("Context")
    
    with st.expander("Scene Structure"):
        st.markdown(st.session_state.get("context_scene_structure", "_No structure available._"))

    with st.expander("Web Context Summary"):
        st.markdown(st.session_state.get("context_web_summary", "_No web context available._"))

    with st.expander("Character List"):
        st.markdown(st.session_state.get("context_characters", "_No character data available._"))

    with st.expander("Scene Synopsis"):
        st.markdown(st.session_state.get("context_scene_summary", "_No synopsis available._"))

    with st.expander("Tone and Style"):
        st.markdown(st.session_state.get("context_tone", "_No tone analysis available._"))
        
def create_context_dict():
    context = {
         "scene_structure": st.session_state.get("context_scene_structure"),
         "characters": st.session_state.get("context_characters"),
         "tone": st.session_state.get("context_tone"),
         "synopsis": st.session_state.get("context_scene_summary"),
         "web_search": st.session_state.get("context_web_summary"),
    }
     
    return context
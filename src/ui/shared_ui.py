import streamlit as st

def show_context():
    st.subheader("Context")
    
    with st.expander("Web Search Results"):
        st.markdown(st.session_state.get("web_context", "_No web context available._"))
    
    with st.expander("Character List"):
        st.markdown(st.session_state.get("character_list", "_No structure available._"))

    with st.expander("High Level Synopsis"):
        st.markdown(st.session_state.get("synopsis", "_No synopsis available._"))
    
        
def get_context_dict():
    context = {
         "character_list": st.session_state.get("character_list"),
         "high_level_synopsis": st.session_state.get("synopsis")
    }
     
    return context
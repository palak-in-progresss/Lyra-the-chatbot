# chatbot/memory.py
import streamlit as st
from chatbot.config import MAX_HISTORY
from chatbot.database import load_messages, save_message, delete_session

def initialize_memory(session_id=None):
    """
    Initializes the chat history in Streamlit session state.
    Loads messages for the active session if state is currently empty.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if not st.session_state.messages and session_id:
        st.session_state.messages = load_messages(session_id, limit=MAX_HISTORY * 2)

def load_session_into_memory(session_id):
    """
    Clears current session state and populates it with the history 
    of the newly selected chat session from the database.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if session_id:
        st.session_state.messages = load_messages(session_id, limit=MAX_HISTORY * 2)
    else:
        st.session_state.messages = []

def get_history(session_id=None):
    """Returns the active chat history."""
    initialize_memory(session_id)
    return st.session_state.messages

def add_message(role, content, mode, user_id=None, session_id=None):
    """
    Adds a new message to the active chat history.
    role: 'user' or 'assistant'
    content: The message text
    mode: The active assistant mode
    user_id: User UUID
    session_id: Active Session UUID
    """
    initialize_memory(session_id)
    
    # 1. Update session state
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "mode": mode
    })
    
    # 2. Save to database using session mapping
    if user_id and session_id:
        save_message(user_id, session_id, role, content, mode)
        
    # 3. Limit active session state size
    prune_history()

def prune_history():
    """Limits the UI chat history queue size."""
    max_messages = MAX_HISTORY * 2
    if len(st.session_state.messages) > max_messages:
        st.session_state.messages = st.session_state.messages[-max_messages:]

def clear_history(session_id=None):
    """
    Deletes the current chat session and clears the UI stream.
    """
    st.session_state.messages = []
    if session_id:
        delete_session(session_id)
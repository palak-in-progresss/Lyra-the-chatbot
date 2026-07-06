# chatbot/memory.py
import streamlit as st
from chatbot.config import MAX_HISTORY
from chatbot.database import load_messages, save_message, delete_messages

def initialize_memory(user_id=None):
    """
    Initializes the chat history in Streamlit session state.
    If session state is empty but a database user_id is provided, 
    it loads recent history from Supabase automatically.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # If session state is empty, attempt to load history from Supabase
    if not st.session_state.messages and user_id:
        db_history = load_messages(user_id, limit=MAX_HISTORY * 2)
        st.session_state.messages = db_history

def get_history(user_id=None):
    """Returns the chat messages, ensuring memory is initialized first."""
    initialize_memory(user_id)
    return st.session_state.messages

def add_message(role, content, mode, user_id=None):
    """
    Adds a new message to the chat history.
    role: 'user' or 'assistant'
    content: The message text
    mode: The active assistant mode at the time of the message
    user_id: The database user UUID (if provided, saves to Supabase)
    """
    initialize_memory(user_id)
    
    # 1. Update session state
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "mode": mode
    })
    
    # 2. Save to Supabase for persistence
    if user_id:
        save_message(user_id, role, content, mode)
        
    # 3. Limit active session state size
    prune_history()

def prune_history():
    """
    Limits active session state history to MAX_HISTORY turns to keep UI fast.
    """
    max_messages = MAX_HISTORY * 2
    if len(st.session_state.messages) > max_messages:
        st.session_state.messages = st.session_state.messages[-max_messages:]

def clear_history(user_id=None):
    """
    Clears the chat history in the active session state 
    and removes history for this user from Supabase.
    """
    st.session_state.messages = []
    if user_id:
        delete_messages(user_id)
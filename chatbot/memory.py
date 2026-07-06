# chatbot/memory.py
import streamlit as st
from chatbot.config import MAX_HISTORY

def initialize_memory():
    """Initializes the chat history in Streamlit session state if not already present."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

def get_history():
    """Returns the full list of chat messages stored in session state."""
    initialize_memory()
    return st.session_state.messages

def add_message(role, content, mode):
    """
    Adds a new message to the chat history.
    role: 'user' or 'assistant'
    content: The message text
    mode: The active assistant mode at the time of the message
    """
    initialize_memory()
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "mode": mode
    })
    prune_history()

def prune_history():
    """
    Limits the history to MAX_HISTORY turns (each turn consists of 1 user message 
    and 1 assistant response). If limit is exceeded, older messages are discarded.
    """
    # 1 turn = 2 messages (user + assistant)
    max_messages = MAX_HISTORY * 2
    if len(st.session_state.messages) > max_messages:
        # Keep the latest max_messages
        st.session_state.messages = st.session_state.messages[-max_messages:]

def clear_history():
    """Clears the chat history in the active session state."""
    st.session_state.messages = []
# chatbot/database.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key is not configured. Please check your .env file.")

# Initialize the Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_or_create_user(user_uuid: str):
    """
    Checks if the user exists in the database. 
    If they do not exist, inserts their anonymous UUID record.
    """
    try:
        response = supabase.table("users").select("id").eq("id", user_uuid).execute()
        if not response.data:
            supabase.table("users").insert({"id": user_uuid}).execute()
        return True
    except Exception as e:
        print(f"Database error in get_or_create_user: {e}")
        return False

def create_session(user_uuid: str, title: str = "New Chat") -> str:
    """
    Creates a new conversation session associated with the user.
    Returns the generated session_id UUID.
    """
    try:
        get_or_create_user(user_uuid)
        response = supabase.table("sessions").insert({
            "user_id": user_uuid,
            "title": title
        }).execute()
        if response.data:
            return response.data[0]["id"]
    except Exception as e:
        print(f"Database error in create_session: {e}")
    return ""

def get_user_sessions(user_uuid: str):
    """
    Retrieves all chat sessions for the user, ordered by creation date (newest first).
    """
    try:
        get_or_create_user(user_uuid)
        response = (
            supabase.table("sessions")
            .select("id, title, created_at")
            .eq("user_id", user_uuid)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"Database error in get_user_sessions: {e}")
        return []

def update_session_title(session_uuid: str, title: str):
    """
    Updates the title of a specific chat session.
    """
    try:
        supabase.table("sessions").update({"title": title}).eq("id", session_uuid).execute()
    except Exception as e:
        print(f"Database error in update_session_title: {e}")

def delete_session(session_uuid: str):
    """
    Deletes a specific chat session (automatically cascade-deletes its messages).
    """
    try:
        supabase.table("sessions").delete().eq("id", session_uuid).execute()
        return True
    except Exception as e:
        print(f"Database error in delete_session: {e}")
        return False

def save_message(user_uuid: str, session_uuid: str, role: str, message: str, mode: str):
    """
    Saves a message associated with both the user and the specific active session.
    """
    try:
        get_or_create_user(user_uuid)
        supabase.table("conversations").insert({
            "user_id": user_uuid,
            "session_id": session_uuid,
            "role": role,
            "message": message,
            "mode": mode
        }).execute()
    except Exception as e:
        print(f"Database error in save_message: {e}")

def load_messages(session_uuid: str, limit: int = 20):
    """
    Loads recent history for a specific chat session, ordered oldest to newest.
    """
    try:
        response = (
            supabase.table("conversations")
            .select("role, message, mode")
            .eq("session_id", session_uuid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        messages = response.data[::-1]
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["message"],
                "mode": msg["mode"]
            })
        return formatted_messages
    except Exception as e:
        print(f"Database error in load_messages: {e}")
        return []
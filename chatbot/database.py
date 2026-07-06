# chatbot/database.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environmental variables
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
        # Check if user already exists
        response = supabase.table("users").select("id").eq("id", user_uuid).execute()
        if not response.data:
            # Register user
            supabase.table("users").insert({"id": user_uuid}).execute()
        return True
    except Exception as e:
        print(f"Database error in get_or_create_user: {e}")
        return False

def save_message(user_uuid: str, role: str, message: str, mode: str):
    """
    Saves a single message turn (user or assistant) into the Supabase database.
    """
    try:
        # First ensure user entry exists
        get_or_create_user(user_uuid)
        
        # Save message
        supabase.table("conversations").insert({
            "user_id": user_uuid,
            "role": role,
            "message": message,
            "mode": mode
        }).execute()
    except Exception as e:
        print(f"Database error in save_message: {e}")

def load_messages(user_uuid: str, limit: int = 20):
    """
    Loads the recent history for the given user, ordered oldest to newest.
    """
    try:
        # Fetch latest messages descending, then reverse to output in chronological order
        response = (
            supabase.table("conversations")
            .select("role, message, mode")
            .eq("user_id", user_uuid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        # Reverse list to maintain oldest -> newest conversation flow
        messages = response.data[::-1]
        
        # Format to match Streamlit's session_state expectation
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

def delete_messages(user_uuid: str):
    """
    Deletes all conversation records associated with the user UUID.
    """
    try:
        supabase.table("conversations").delete().eq("user_id", user_uuid).execute()
        return True
    except Exception as e:
        print(f"Database error in delete_messages: {e}")
        return False
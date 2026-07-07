# chatbot/llm.py
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from chatbot.config import MODEL_NAME
from chatbot.prompts import build_system_prompt
from chatbot.memory import get_history

# Load environment variables from .env file
load_dotenv()

# Retrieve API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "your_gemini_api_key_here":
    raise ValueError("GEMINI_API_KEY is not configured. Please check your .env file.")

# Initialize the modern Gemini Client
client = genai.Client(api_key=api_key)

def generate_response(user_input, mode):
    """
    Sends the user input along with chat history and compiled system instructions 
    to the Gemini API using the modern google-genai SDK.
    """
    # 1. Build the system prompt for the active mode
    system_instruction = build_system_prompt(mode)
    
    # 2. Get and format conversation history for the Gemini Client
    history = get_history()
    gemini_history = []
    
    for msg in history:
        gemini_role = "model" if msg["role"] == "assistant" else "user"
        # Structure the history content using the new SDK types
        gemini_history.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    
    try:
        # 3. Create a chat session with Google Search Grounding enabled
        chat = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())]  # Correct modern Search Grounding format
            ),
            history=gemini_history
        )
        
        # 4. Send the new user message to the chat
        response = chat.send_message(user_input)
        
        return response.text
        
    except Exception as e:
        error_msg = f"Sorry! I encountered an error communicating with Gemini. Details: {str(e)}"
        print(f"Error in LLM Call: {e}")
        return error_msg
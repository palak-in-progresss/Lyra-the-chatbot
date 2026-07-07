# chatbot/llm.py
import os
import google.generativeai as genai
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

# Configure the Google GenerativeAI library
genai.configure(api_key=api_key)

def generate_response(user_input, mode):
    """
    Sends the user input along with chat history and compiled system instructions 
    to the Gemini API with Google Search Grounding enabled.
    """
    # 1. Build the system prompt for the active mode
    system_instruction = build_system_prompt(mode)
    
    # 2. Get and format conversation history for the Gemini API
    history = get_history()
    gemini_history = []
    
    for msg in history:
        gemini_role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({
            "role": gemini_role,
            "parts": [msg["content"]]
        })
    
    try:
        # 3. Initialize the Gemini Model with system instruction and Google Search Grounding
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_instruction,
            tools=[{"google_search": {}}]  # Correct legacy format for search grounding
        )
        
        # 4. Start the chat session with existing history
        chat = model.start_chat(history=gemini_history)
        
        # 5. Send the new user message to the model
        response = chat.send_message(user_input)
        
        return response.text
        
    except Exception as e:
        error_msg = f"Sorry! I encountered an error communicating with Gemini. Details: {str(e)}"
        print(f"Error in LLM Call: {e}")
        return error_msg
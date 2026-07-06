# chatbot/prompts.py
import os

# Define the absolute path of the prompts directory relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

# Mapping from mode names in config to prompt filenames
MODE_FILE_MAP = {
    "General Assistant": "general.txt",
    "Study Buddy": "study.txt",
    "DSA Helper": "dsa.txt",
    "Career Mentor": "career.txt",
    "Resume Reviewer": "resume.txt",
    "Space Mentor": "space.txt"
}

def load_prompt_file(filename):
    """Helper function to load content from a file in the prompts directory."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        # Fallback to empty string if file is missing
        return ""

def build_system_prompt(mode):
    """
    Combines the Lyra base personality prompt with the specific instructions 
    for the selected assistant mode.
    """
    base_prompt = load_prompt_file("base.txt")
    
    # Get the file name for the requested mode, fallback to general if not found
    mode_filename = MODE_FILE_MAP.get(mode, "general.txt")
    mode_prompt = load_prompt_file(mode_filename)
    
    # Combine the base personality and mode specific prompt
    compiled_prompt = f"{base_prompt}\n\n{mode_prompt}"
    return compiled_prompt
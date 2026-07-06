# chatbot/config.py

# Name of the application
APP_NAME = "Lyra"

# The Gemini model version we want to use
MODEL_NAME = "gemini-2.5-flash"

# Maximum conversation turns (User + Assistant exchange pairs) to keep in the session state
MAX_HISTORY = 20

# Available chatbot assistance modes
AVAILABLE_MODES = [
    "General Assistant",
    "Study Buddy",
    "DSA Helper",
    "Career Mentor",
    "Resume Reviewer",
    "Space Mentor"
]
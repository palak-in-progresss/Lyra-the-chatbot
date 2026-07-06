# chatbot/utils.py

def clean_response(text):
    """
    Cleans and formats response text from the LLM.
    Ensures standard formatting matches requirements.
    """
    if not text:
        return ""
    return text.strip()

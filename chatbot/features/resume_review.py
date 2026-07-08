# chatbot/features/resume_review.py
import os
from pypdf import PdfReader
from google import genai
from google.genai import types
from dotenv import load_dotenv
from chatbot.config import MODEL_NAME
from chatbot.prompts import build_system_prompt

# Load environment variables
load_dotenv()

# Retrieve API key
api_key = os.getenv("GEMINI_API_KEY")

# Initialize modern Gemini Client
client = genai.Client(api_key=api_key)

import io

def extract_text_from_pdf(pdf_file):
    """
    Extracts text from an uploaded PDF file stream.
    Supports file-like objects and raw bytes.
    """
    try:
        if isinstance(pdf_file, bytes):
            pdf_file = io.BytesIO(pdf_file)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def evaluate_resume(resume_text):
    """
    Composes a structured prompt with the extracted resume text, 
    sends it to Gemini using the Resume Reviewer persona, and returns the analysis.
    """
    if not resume_text:
        return "No text could be extracted from the resume. Please check if the PDF is scanned or empty."
        
    # Get the system instruction for the Resume Reviewer mode
    system_instruction = build_system_prompt("Resume Reviewer")
    
    # Compose the prompt
    prompt = f"""
    Please evaluate the following resume content in detail. Format your response clearly using Markdown headings.
    
    Provide the following sections:
    1. **Strengths**: What is done well (formatting, phrasing, impact).
    2. **Weaknesses**: Areas that need improvement (vague descriptions, formatting issues, lack of metrics).
    3. **Actionable Suggestions**: Concrete wording changes or phrasing improvements.
    4. **ATS Recommendations**: How compatible this resume is with Applicant Tracking Systems, and how to improve parsing.
    5. **Missing Skills**: Crucial technologies, methodologies, or certifications that are standard in this candidate's field but missing here.
 
    Resume Content:
    ---
    {resume_text}
    ---
    """
    
    try:
        # Generate the analysis using the modern SDK
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text
        
    except Exception as e:
        error_msg = f"Sorry! I encountered an error analyzing the resume. Details: {str(e)}"
        print(f"Error in Resume LLM call: {e}")
        return error_msg

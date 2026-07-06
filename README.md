# Lyra - Conversational AI Learning Assistant

Lyra is a professional, portfolio-grade conversational AI assistant built using **Python, Streamlit, and the Google Gemini API**. Designed specifically for students and junior developers, Lyra integrates a consistent personality with multiple specialized assistance modes.

---

## 🌟 Features

### 1. Consistent Personality
No matter the mode, Lyra maintains a **friendly, intelligent, encouraging, and slightly witty** persona. She explains complex technical concepts simply, using clear analogies.

### 2. Multi-Mode Expertise
Using a sidebar selector, users can switch the active expertise mode. Each mode triggers tailored system instructions:
* **🤖 General Assistant:** General concepts, brainstorming, and creative tasks.
* **🎓 Study Buddy:** Summarization, active recall quizzes, and interactive learning.
* **💻 DSA Helper:** Step-by-step algorithms and data structures guidance. Lyra uses hint-based support rather than giving away code directly, and provides Big-O time/space complexity analysis.
* **💼 Career Mentor:** Guidance on tech paths, project ideas, portfolio building, and interview preparation.
* **📄 Resume Reviewer:** PDF resume text extraction and detailed evaluation (Strengths, Weaknesses, Actionable suggestions, ATS keywords, and Missing skills).
* **🌌 Space Mentor:** Astronomy, astrophysics, and stargazing recommendations. Includes custom generated quizzes.

### 3. Active Conversation Memory
Manages context state dynamically within Streamlit's `st.session_state` to enable natural dialogue. Prunes history automatically to stay within a configurable limit (`MAX_HISTORY` turns) to avoid token bloat and control latency.

### 4. Interactive Resume Conversations
When you upload a PDF in the Resume Reviewer mode, the analysis is printed directly into the chat log. This allows you to ask follow-up questions about Lyra's critique (e.g., *"How can I rephrase my project to include the missing skills you mentioned?"*).

---

## 🛠️ Tech Stack

* **Frontend:** Streamlit
* **AI Model:** Gemini 1.5 Flash (via the official `google-generativeai` SDK)
* **PDF Parser:** PyPDF (robust text extraction from byte streams)
* **Environment Configuration:** python-dotenv

---

## 📁 Project Directory Structure

```text
lyra/
├── app.py                      # Main Streamlit frontend app
├── chatbot/                    # Core backend logic package
│   ├── __init__.py             # Package initializer
│   ├── config.py               # Constants (MODEL_NAME, MAX_HISTORY, AVAILABLE_MODES)
│   ├── llm.py                  # Gemini API connection and session management
│   ├── memory.py               # Memory state manager (pruning, clearing)
│   ├── prompts.py              # System prompt builder (personality + mode compiler)
│   ├── features/               # Specialized features sub-package
│   │   ├── __init__.py         # Features initializer
│   │   └── resume_review.py    # PDF extraction and resume reviewer logic
│   └── utils.py                # Formatting and text cleaning helpers
├── prompts/                    # Raw system prompt text files
│   ├── base.txt                # Lyra base persona
│   ├── general.txt             # General assistant specific guidelines
│   ├── study.txt               # Study buddy guidelines
│   ├── dsa.txt                 # DSA helper rules (hint-based guidance)
│   ├── career.txt              # Career mentor guidelines
│   ├── resume.txt              # Resume critique guidelines
│   └── space.txt               # Space mentoring and quiz details
├── data/                       # Storage placeholder
│   └── memory.json             # Future persistent storage configuration
├── assets/                     # Screenshots and graphics for documentation
├── .env                        # Local environment variables (ignored in Git)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 Installation & Setup

Follow these steps to run Lyra locally:

### 1. Prerequisite
Ensure you have **Python 3.9+** installed on your system.

### 2. Set Up the Project
Create a folder for the project and download/place the files matching the structure above.

### 3. Install Dependencies
Open your terminal in the project root directory and run:
```bash
pip install -r requirements.txt
```

### 4. Configure Your API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_actual_gemini_key_here
```
*(Get a free API key in seconds from [Google AI Studio](https://aistudio.google.com/)).*

### 5. Launch the Application
Start the Streamlit local server:
```bash
streamlit run app.py
```
A browser tab will automatically open at `http://localhost:8501`.

---

## 📸 Screenshots Placeholder
*Add your app screenshots here to showcase your project to recruiters!*

---

## 🔮 Future-Ready Architecture
Lyra has been structured with future scalability in mind:
* **Long-Term Memory:** The `data/memory.json` placeholder can be replaced with a SQLite database to remember conversations across browser sessions.
* **User Authentication:** Ready for OAuth2 or Firebase integrations.
* **RAG (Retrieval-Augmented Generation):** The `chatbot/features/` folder is designed to easily plug in a vector database (like Chroma or FAISS) for document search.
* **Voice input/output:** Ready to plug in speech-to-text libraries.

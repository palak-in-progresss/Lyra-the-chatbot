# app.py
import streamlit as st
import os

from chatbot.config import APP_NAME, AVAILABLE_MODES
from chatbot.database import (
    create_session,
    get_user_sessions,
    update_session_title,
    delete_session,
    supabase,
    get_or_create_user
)
from chatbot.memory import (
    initialize_memory,
    get_history,
    add_message,
    clear_history,
    load_session_into_memory
)
from chatbot.llm import generate_response
from chatbot.features.resume_review import extract_text_from_pdf, evaluate_resume
from chatbot.utils import clean_response

# 1. Page Configuration (Must be first Streamlit command)
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🌌",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Authentication UI & Persistent Login (Bypasses session reset on tab close)
# Initialize session state cache for user_id and email
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Priority 1: Try to load saved session from URL query parameters
query_params = st.query_params
if "uid" in query_params and "email" in query_params:
    st.session_state.user_id = query_params["uid"]
    st.session_state.user_email = query_params["email"]

# Priority 2: Use browser LocalStorage to persist session across tab closes (cookie-free)
# We inject a native DOM script. If a session is found in localStorage and we don't have uid in query params,
# we redirect the page directly to append the query params. If 'logout=true' is in the URL, we clear storage.
if st.session_state.user_id is None:
    st.html(
        """
        <img src="x" onerror="
        try {
            var urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('logout') === 'true') {
                localStorage.removeItem('lyra_auth_session');
            } else {
                var session = localStorage.getItem('lyra_auth_session');
                if (session && session.indexOf('|') !== -1) {
                    var parts = session.split('|');
                    if (!urlParams.has('uid')) {
                        urlParams.set('uid', parts[0]);
                        urlParams.set('email', parts[1]);
                        window.location.replace(window.location.pathname + '?' + urlParams.toString());
                    }
                }
            }
        } catch(e) {
            console.error('LocalStorage redirect error:', e);
        }
        " style="display:none;"/>
        """
    )

# If user is not logged in, render the Auth Page
if st.session_state.user_id is None:
    st.markdown("<h1 class='title-gradient' style='text-align:center;'>Welcome to Lyra</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94A3B8; margin-bottom:30px;'>Your AI Study and Coding Companion</p>", unsafe_allow_html=True)
    
    # Beautiful auth container tab switcher
    auth_tab = st.tabs(["🔒 Log In", "📝 Sign Up"])
    
    # LOGIN TAB
    with auth_tab[0]:
        st.markdown("<h3 style='color:#FFFFFF; margin-top:10px;'>Access Your Account</h3>", unsafe_allow_html=True)
        login_email = st.text_input("Email Address", key="login_email_input")
        login_password = st.text_input("Password", type="password", key="login_password_input")
        
        if st.button("🚀 Log In", use_container_width=True, key="login_submit_btn"):
            if not login_email or not login_password:
                st.error("Please enter both email and password.")
            else:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": login_email,
                        "password": login_password
                    })
                    # Set session state
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    
                    # Sync to URL for tab-close persistence
                    st.query_params["uid"] = response.user.id
                    st.query_params["email"] = response.user.email
                    
                    st.success("Welcome back!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
                    
    # SIGNUP TAB
    with auth_tab[1]:
        st.markdown("<h3 style='color:#FFFFFF; margin-top:10px;'>Create a New Account</h3>", unsafe_allow_html=True)
        signup_email = st.text_input("Email Address", key="signup_email_input")
        signup_password = st.text_input("Password (min 6 characters)", type="password", key="signup_password_input")
        
        if st.button("✨ Sign Up", use_container_width=True, key="signup_submit_btn"):
            if not signup_email or not signup_password:
                st.error("Please enter both email and password.")
            elif len(signup_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    response = supabase.auth.sign_up({
                        "email": signup_email,
                        "password": signup_password
                    })
                    # Set session state
                    st.session_state.user_id = response.user.id
                    st.session_state.user_email = response.user.email
                    
                    # Sync to URL for tab-close persistence
                    st.query_params["uid"] = response.user.id
                    st.query_params["email"] = response.user.email
                    
                    # Initialize in public.users table
                    get_or_create_user(response.user.id)
                    st.success("Account created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Signup failed: {e}")
                    
    st.stop()  # Stop rendering the rest of the page if not logged in

# Set user_id from session state
user_id = st.session_state.user_id

# Declarative localStorage sync: if logged in, ensure localStorage is up to date
if user_id is not None:
    session_val = f"{st.session_state.user_id}|{st.session_state.user_email}"
    st.html(
        f"""
        <img src="x" onerror="
        try {{
            if (localStorage.getItem('lyra_auth_session') !== '{session_val}') {{
                localStorage.setItem('lyra_auth_session', '{session_val}');
            }}
        }} catch(e) {{
            console.error(e);
        }}
        " style="display:none;"/>
        """
    )

# 3. Session (Conversation Thread) Management
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None

# Fetch all sessions for this user from Supabase
user_sessions = get_user_sessions(user_id)

# If no sessions exist in the database, create the first one
if not user_sessions:
    first_session_id = create_session(user_id, "New Chat")
    st.session_state.active_session_id = first_session_id
    user_sessions = get_user_sessions(user_id)
# If a session ID is not active yet, default to the latest session
elif st.session_state.active_session_id is None:
    st.session_state.active_session_id = user_sessions[0]["id"]

# Retrieve the active session ID
active_session_id = st.session_state.active_session_id

# Load the active session's conversation from database if empty
initialize_memory(active_session_id)

# 4. Modern UI Aesthetics (CSS injection)
st.markdown("""
<style>
    /* Import modern Outfit font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global theme */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
        min-height: 100vh;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.2);
    }

    /* Title gradient text */
    .title-gradient {
        background: linear-gradient(135deg, #818CF8, #A78BFA, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .subtitle-text {
        color: #94A3B8;
        font-size: 1.05rem;
        font-weight: 400;
        margin-top: -10px;
    }

    /* Chat message styling */
    .stChatMessage {
        background: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        margin-bottom: 8px;
    }

    /* Input box styling */
    .stChatInputContainer {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
    }

    /* Primary button */
    .stButton > button[kind="primary"],
    .stButton > button {
        background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
    }

    /* Session cards in sidebar */
    .session-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .session-card:hover {
        background: rgba(99, 102, 241, 0.15);
        border-color: rgba(99, 102, 241, 0.4);
    }

    .session-card.active {
        background: rgba(99, 102, 241, 0.2);
        border-color: #6366F1;
    }

    /* Welcome card */
    .welcome-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 28px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }

    /* Mode selector */
    [data-testid="stSelectbox"] {
        background: rgba(30, 41, 59, 0.6);
    }

    /* Divider */
    hr {
        border-color: rgba(99, 102, 241, 0.2) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 5. Sidebar Layout
with st.sidebar:
    st.markdown("<h2 class='title-gradient' style='margin-bottom:5px;'>🌌 Lyra</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B; font-size:0.8rem; margin-top:0;'>Your AI Study Companion</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Mode Selector
    st.markdown("<p style='color:#94A3B8; font-size:0.85rem; margin-bottom:5px;'>🎯 Active Mode</p>", unsafe_allow_html=True)
    selected_mode = st.selectbox(
        "Mode",
        options=AVAILABLE_MODES,
        label_visibility="collapsed",
        key="mode_selector"
    )
    
    st.divider()
    
    # Conversation sessions
    st.markdown("<p style='color:#94A3B8; font-size:0.85rem;'>💬 Conversations</p>", unsafe_allow_html=True)
    
    if st.button("➕ New Chat", use_container_width=True):
        new_session_id = create_session(user_id, "New Chat")
        st.session_state.active_session_id = new_session_id
        clear_history(new_session_id)
        st.rerun()
    
    st.markdown("")
    
    for session in user_sessions:
        session_id = session["id"]
        title = session.get("title", "New Chat")
        is_active = session_id == active_session_id
        
        col1, col2 = st.columns([4, 1])
        with col1:
            label = f"{'▶ ' if is_active else ''}{title[:28]}{'...' if len(title) > 28 else ''}"
            if st.button(label, key=f"session_{session_id}", use_container_width=True):
                st.session_state.active_session_id = session_id
                load_session_into_memory(session_id)
                st.rerun()
        with col2:
            if st.button("🗑", key=f"del_{session_id}", help="Delete this chat"):
                delete_session(session_id)
                if is_active:
                    st.session_state.active_session_id = None
                st.rerun()
    
    # Resume upload for Resume Reviewer mode
    if selected_mode == "📄 Resume Reviewer":
        st.divider()
        st.markdown("<p style='color:#94A3B8; font-size:0.85rem;'>📎 Upload Resume</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("🔍 Analyze Resume", use_container_width=True):
                with st.spinner("Analyzing your resume..."):
                    resume_text = extract_text_from_pdf(uploaded_file.read())
                    if resume_text:
                        critique = evaluate_resume(resume_text)
                        add_message("user", f"Uploaded resume '{uploaded_file.name}' for critique.", "Resume Reviewer", user_id, active_session_id)
                        add_message("assistant", critique, "Resume Reviewer", user_id, active_session_id)
                        st.success("Analysis complete! Review the results in the chat below.")
                        st.rerun()
                    else:
                        st.error("Failed to read the PDF. Make sure it contains extractable text.")

    # Logout section in sidebar
    st.divider()
    st.markdown(f"<p style='color:#64748B; font-size:0.85rem; margin-bottom:5px;'>👤 Logged in as:<br><b style='color:#E2E8F0;'>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Log Out", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except:
            pass
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.active_session_id = None
        st.session_state.messages = []
        st.query_params.clear()
        st.query_params["logout"] = "true"  # Signals redirector to clear localStorage
        st.rerun()

# 6. Main Content Header
st.markdown("<h1 class='title-gradient'>Lyra</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='subtitle-text'>Friendly, intelligent, and witty AI companion.</p>", unsafe_allow_html=True)

# Retrieve conversation history for active session
history = get_history(active_session_id)

# Show welcome greeting if there are no messages in the active session
if not history:
    st.markdown(f"""
    <div class="welcome-card">
        <h3 style="color:#FFFFFF; margin-top:0;">Hi, I'm {APP_NAME}! 🌌</h3>
        <p style="color:#94A3B8; font-size:0.95rem;">
            I am here to assist you in learning, coding, and building projects. 
            Select one of my specialized modes in the sidebar to start a conversation:
        </p>
        <ul style="color:#94A3B8; font-size:0.9rem; padding-left:20px;">
            <li><b>General Assistant:</b> General brainstorms or writing code.</li>
            <li><b>Study Buddy:</b> Active learning recall and note breakdowns.</li>
            <li><b>DSA Helper:</b> Hint-based guidance and Big-O reviews.</li>
            <li><b>Career Mentor:</b> Project ideas and interview prep tips.</li>
            <li><b>Resume Reviewer:</b> Actionable suggestions for your PDF resume.</li>
            <li><b>Space Mentor:</b> Explore cosmology, astrophysics, and stars.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# 7. Render Chat History
for msg in history:
    role = msg["role"]
    content = msg["content"]
    with st.chat_message(role):
        st.markdown(content)

# 8. Chat Input
prompt = st.chat_input(f"Ask Lyra anything in {selected_mode} mode...")

if prompt:
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Save user message to DB
    add_message("user", prompt, selected_mode, user_id, active_session_id)
    
    # Auto-title session from first message
    if len(history) == 0:
        title_preview = prompt[:40] + ("..." if len(prompt) > 40 else "")
        update_session_title(active_session_id, title_preview)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Lyra is thinking..."):
            response_text = generate_response(prompt, selected_mode, active_session_id)
            cleaned = clean_response(response_text)
            st.markdown(cleaned)
    
    # Save assistant message to DB
    add_message("assistant", cleaned, selected_mode, user_id, active_session_id)
    
    st.rerun()
# app.py
import streamlit as st
import os
import uuid
import time

from chatbot.config import APP_NAME, AVAILABLE_MODES
from chatbot.database import (
    create_session, 
    get_user_sessions, 
    update_session_title, 
    delete_session
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

# Priority 1: Try to load saved session from URL query parameters (backup)
query_params = st.query_params
if "uid" in query_params and "email" in query_params:
    st.session_state.user_id = query_params["uid"]
    st.session_state.user_email = query_params["email"]

# Priority 2: Use browser LocalStorage to persist session across tab closes (cookie-free)
from streamlit_javascript import st_javascript

js_get_code = """
(function() {
    try {
        var s = window.parent.localStorage.getItem("lyra_auth_session");
        if (s) return s;
    } catch(e) {}
    try {
        var s2 = localStorage.getItem("lyra_auth_session");
        if (s2) return s2;
    } catch(e) {}
    return "NO_SESSION";
})()
"""

# If URL is clean, fetch from browser local storage
if st.session_state.user_id is None:
    js_val = st_javascript(js_get_code, key="get_local_storage_session")
    if js_val == 0:
        # Component is still loading in browser, show loader and stop
        st.info("🌌 Loading your Lyra profile...")
        st.stop()
    elif js_val and js_val != "NO_SESSION":
        try:
            if "|" in js_val:
                saved_user_id, saved_user_email = js_val.split("|", 1)
                st.session_state.user_id = saved_user_id
                st.session_state.user_email = saved_user_email
                # Write to query params so subsequent navigation is instant
                st.query_params["uid"] = saved_user_id
                st.query_params["email"] = saved_user_email
        except Exception as e:
            print(f"Error parsing local storage auth session: {e}")

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
                    from chatbot.database import supabase
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
                    
                    # Save to local storage using st_javascript
                    session_val = f"{response.user.id}|{response.user.email}"
                    js_set_code = f"""
                    (function() {{
                        try {{
                            window.parent.localStorage.setItem("lyra_auth_session", "{session_val}");
                        }} catch(e) {{}}
                        try {{
                            localStorage.setItem("lyra_auth_session", "{session_val}");
                        }} catch(e) {{}}
                        return true;
                    }})()
                    """
                    st_javascript(js_set_code, key="set_login_storage_session")
                    
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
                    from chatbot.database import supabase, get_or_create_user
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
                    
                    # Save to local storage using st_javascript
                    session_val = f"{response.user.id}|{response.user.email}"
                    js_signup_set = f"""
                    (function() {{
                        try {{
                            window.parent.localStorage.setItem("lyra_auth_session", "{session_val}");
                        }} catch(e) {{}}
                        try {{
                            localStorage.setItem("lyra_auth_session", "{session_val}");
                        }} catch(e) {{}}
                        return true;
                    }})()
                    """
                    st_javascript(js_signup_set, key="set_signup_storage_session")
                    
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
    js_sync_code = f"""
    (function() {{
        try {{
            if (window.parent.localStorage.getItem("lyra_auth_session") !== "{session_val}") {{
                window.parent.localStorage.setItem("lyra_auth_session", "{session_val}");
            }}
        }} catch(e) {{}}
        try {{
            if (localStorage.getItem("lyra_auth_session") !== "{session_val}") {{
                localStorage.setItem("lyra_auth_session", "{session_val}");
            }}
        }} catch(e) {{}}
        return true;
    }})()
    """
    st_javascript(js_sync_code, key="sync_local_storage_session")

# 3. Session (Conversation Thread) Management
# Initialize active session ID cache if not present
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
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Title styling with gradient text */
    .title-gradient {
        background: linear-gradient(135deg, #A855F7, #3B82F6, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.2rem;
        margin-bottom: 0px;
        padding-bottom: 5px;
    }
    
    .subtitle-text {
        font-size: 1.1rem;
        color: #94A3B8;
        margin-top: -5px;
        margin-bottom: 25px;
        font-weight: 400;
    }
    
    /* Mode Pill Badge in Chat bubbles */
    .mode-badge {
        font-size: 0.7rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        color: #FFFFFF;
        display: inline-block;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-general-assistant { background-color: #6366F1; }
    .badge-study-buddy { background-color: #EF4444; }
    .badge-dsa-helper { background-color: #3B82F6; }
    .badge-career-mentor { background-color: #10B981; }
    .badge-resume-reviewer { background-color: #F97316; }
    .badge-space-mentor { background-color: #8B5CF6; }
    
    /* Card design for welcome greeting */
    .welcome-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-top: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
    
    /* Sidebar styling tweaks */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
</style>
""", unsafe_allow_html=True)

# 5. Sidebar Construction
with st.sidebar:
    st.markdown(f"<h2 style='color:#FFFFFF; font-weight:800; margin-bottom:0;'>✨ {APP_NAME}</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B; font-size:0.9rem; margin-top:0;'>Your AI Learning Assistant</p>", unsafe_allow_html=True)
    st.divider()
    

    # ➕ Create a New Session Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_sid = create_session(user_id, "New Chat")
        st.session_state.active_session_id = new_sid
        load_session_into_memory(new_sid)
        st.rerun()
        
    st.divider()
    
    # List of Past Chats (ChatGPT Style Sidebar)
    st.markdown("<p style='color:#64748B; font-size:0.85rem; font-weight:600; margin-bottom:10px;'>RECENT CHATS</p>", unsafe_allow_html=True)
    for s in user_sessions:
        is_active = (s["id"] == active_session_id)
        btn_label = f"💬 {s['title']}"
        
        # Grid layout for selecting a session and a trash button to delete it
        col_btn, col_del = st.columns([0.83, 0.17])
        with col_btn:
            if st.button(
                btn_label, 
                key=f"select_{s['id']}", 
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_session_id = s["id"]
                load_session_into_memory(s["id"])
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{s['id']}", help="Delete this chat session"):
                delete_session(s["id"])
                # If deleted active session, fallback to latest or clear
                if s["id"] == active_session_id:
                    st.session_state.active_session_id = None
                st.rerun()
                
    st.divider()
    
    # Mode selection
    selected_mode = st.selectbox(
        "Choose Mode",
        options=AVAILABLE_MODES,
        index=0
    )
    
    # Mode information card
    info = MODE_INFO = {
        "General Assistant": {
            "description": "Brainstorm, check code, or ask general questions. Lyra is in her standard creative mode.",
            "icon": "🤖"
        },
        "Study Buddy": {
            "description": "Lyra acts as an interactive study companion, helping you break down topics and testing your recall.",
            "icon": "🎓"
        },
        "DSA Helper": {
            "description": "Explain logic, debug algorithms, and review Big-O. Lyra guides you with hints instead of direct answers.",
            "icon": "💻"
        },
        "Career Mentor": {
            "description": "Receive resume-building strategies, portfolio ideas, and industry guidance for tech domains.",
            "icon": "💼"
        },
        "Resume Reviewer": {
            "description": "Upload your resume in PDF format to receive Strengths, Weaknesses, Actionable suggestions, and ATS keywords.",
            "icon": "📄"
        },
        "Space Mentor": {
            "description": "Learn astronomy, astrophysics, and cosmology. Ask Lyra for quizzes or telescope recommendations!",
            "icon": "🌌"
        }
    }.get(selected_mode, {"description": "", "icon": "🤖"})
    
    st.markdown(f"""
    <div style='background-color:#1E293B; border:1px solid #334155; border-radius:12px; padding:15px; margin-top:10px; margin-bottom:15px;'>
        <h4 style='color:#FFFFFF; margin:0;'>{info["icon"]} {selected_mode}</h4>
        <p style='color:#94A3B8; font-size:0.85rem; margin-top:5px; margin-bottom:0;'>{info["description"]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload panel for Resume Reviewer Mode
    if selected_mode == "Resume Reviewer":
        st.markdown("<h4 style='color:#FFFFFF;'>📄 Resume Upload</h4>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload your technical resume (PDF)",
            type=["pdf"],
            help="Upload a PDF copy of your resume to start the review."
        )
        
        if uploaded_file is not None:
            if st.button("🚀 Analyze Resume", use_container_width=True):
                with st.spinner("Extracting text and evaluating resume..."):
                    resume_text = extract_text_from_pdf(uploaded_file)
                    if resume_text:
                        # Auto-title first message if session is default
                        active_session_title = next((s["title"] for s in user_sessions if s["id"] == active_session_id), "New Chat")
                        if active_session_title == "New Chat":
                            update_session_title(active_session_id, f"Resume: {uploaded_file.name[:15]}")
                            
                        # Generate the critique
                        critique = evaluate_resume(resume_text)
                        
                        # Add critique to active session
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
        from chatbot.database import supabase
        try:
            supabase.auth.sign_out()
        except:
            pass
        # Clear local storage using st_javascript & query parameters
        js_clear_code = """
        (function() {
            try {
                window.parent.localStorage.removeItem("lyra_auth_session");
            } catch(e) {}
            try {
                localStorage.removeItem("lyra_auth_session");
            } catch(e) {}
            return true;
        })()
        """
        st_javascript(js_clear_code, key="clear_logout_storage_session")
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.active_session_id = None
        st.session_state.messages = []
        st.query_params.clear()
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

# 7. Render Chat Messages from active session history
for msg in history:
    role = msg["role"]
    content = msg["content"]
    msg_mode = msg.get("mode", "General Assistant")
    
    # Generate mode-specific badge CSS classes
    mode_slug = msg_mode.lower().replace(" ", "-")
    badge_class = f"badge-{mode_slug}"
    
    with st.chat_message(role):
        st.markdown(f'<span class="mode-badge {badge_class}">{msg_mode}</span>', unsafe_allow_html=True)
        st.markdown(content)

# 8. Accept User Chat Input
user_input = st.chat_input("Say something to Lyra...")

if user_input:
    # Auto-title: If this is the very first message of a "New Chat", rename the session
    active_session_title = next((s["title"] for s in user_sessions if s["id"] == active_session_id), "New Chat")
    if active_session_title == "New Chat":
        # Generate title from the first 22 chars of first query
        generated_title = user_input[:20] + "..." if len(user_input) > 20 else user_input
        update_session_title(active_session_id, generated_title)

    # Append user message to memory (session state + Supabase) & display
    add_message("user", user_input, selected_mode, user_id, active_session_id)
    
    # Rerun page to display new user message immediately before LLM call
    st.rerun()

# Check if last message was from user to prompt LLM response
if history and history[-1]["role"] == "user":
    last_msg = history[-1]
    last_mode = last_msg.get("mode", selected_mode)
    
    with st.chat_message("assistant"):
        # Display badge corresponding to the response mode
        mode_slug = last_mode.lower().replace(" ", "-")
        badge_class = f"badge-{mode_slug}"
        st.markdown(f'<span class="mode-badge {badge_class}">{last_mode}</span>', unsafe_allow_html=True)
        
        # Display thinking status
        with st.spinner(f"Lyra is typing ({last_mode})..."):
            response = generate_response(last_msg["content"], last_mode)
            cleaned = clean_response(response)
            
            st.markdown(cleaned)
            
            # Save assistant response to memory (session state + Supabase)
            add_message("assistant", cleaned, last_mode, user_id, active_session_id)
            
            st.rerun()
import os
import datetime
import streamlit as st
from pypdf import PdfReader
from groq import Groq

# Constants
PAGE_TITLE = "AI Roaster & Career Assistant"
PAGE_ICON = "🤖"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE
)

# ⚡ RESPONSIVE CSS & DOM CLEANUP
st.markdown("""
<style>
    /* Complete DOM Hiding via CSS */
    #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], 
    [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stAppHeader,
    div[class*="stAppHeader"], div[class*="ViewerBadge"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Responsive Main Container Padding */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Brand Header - Fluid & Responsive Typography */
    .brand-header {
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 0 10px;
    }
    
    .brand-title {
        /* Screen width ke hisab se font size smooth change hoga */
        font-size: clamp(1.5rem, 5vw, 2.4rem) !important;
        font-weight: 800 !important;
        color: #F0F6FC !important;
        letter-spacing: -0.5px;
        line-height: 1.25 !important;
        word-wrap: break-word;
    }
    
    .brand-subtitle {
        color: #8B949E;
        font-size: clamp(0.85rem, 2.5vw, 1rem) !important;
        margin-top: 6px;
        line-height: 1.4;
    }

    /* Responsive Cards Layout */
    .mode-card {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        height: 100%;
        word-wrap: break-word;
    }
    
    .mode-card h4 {
        color: #F0F6FC;
        font-size: clamp(1rem, 3vw, 1.15rem);
        font-weight: 600;
        margin-top: 0;
        margin-bottom: 8px;
    }
    
    .mode-card p {
        color: #8B949E;
        font-size: clamp(0.8rem, 2.5vw, 0.9rem);
        margin-bottom: 0;
        line-height: 1.4;
    }

    /* Responsive Buttons & Elements */
    .stButton>button {
        border-radius: 8px !important;
        background-color: #21262D !important;
        color: #C9D1D9 !important;
        border: 1px solid #30363D !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
    }
    
    .stButton>button:hover {
        background-color: #30363D !important;
        border-color: #8B949E !important;
        color: #FFFFFF !important;
    }
    
    .pro-badge {
        background-color: #238636;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }

    /* Mobile Specific Overrides */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Force two-column layout to wrap on mobile devices */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 10px;
        }
    }
</style>

<!-- JS Fallback for Header Cleanup -->
<script>
    const removeHeader = () => {
        const headers = document.querySelectorAll('header, [data-testid="stHeader"], [data-testid="stToolbar"]');
        headers.forEach(h => h.remove());
    };
    setInterval(removeHeader, 300);
</script>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS & AI ENGINE
# ==========================================
def read_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text if text.strip() else None
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def get_effective_api_key():
    MY_GROQ_KEY = ""
    
    try:
        if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
        
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key:
        return env_key
        
    return MY_GROQ_KEY

def call_groq_with_fallback(client, messages, temperature=0.7, max_tokens=1500):
    try:
        return client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "rate_limit" in error_msg or "tokens" in error_msg:
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise e

def generate_chat_title(first_user_msg):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "New Chat"
    try:
        client = Groq(api_key=effective_key)
        prompt = f"Summarize this input into a short 2 to 4 word chat title. ONLY return the title text: '{first_user_msg[:150]}'"
        completion = call_groq_with_fallback(
            client, 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=15
        )
        title = completion.choices[0].message.content.strip().replace('"', '')
        return title[:28]
    except Exception:
        cleaned = first_user_msg.strip().split("\n")[0]
        return cleaned[:22] + "..." if len(cleaned) > 22 else cleaned

def get_ai_response(messages_history, active_mode, roast_level, language):
    effective_key = get_effective_api_key()
    
    if not effective_key:
        return "⚠️ **Error:** API Key missing."

    try:
        client = Groq(api_key=effective_key)

        if active_mode == "🧠 Thinking & Career Assistant":
            persona_instructions = """
            YOU ARE A PROFESSIONAL CAREER ASSISTANT & ATS EXPERT.
            - Tone: Highly professional, encouraging, objective, polite, and constructive.
            - DO NOT roast, insult, joke, or humiliate the user.
            - Provide clear, actionable career advice, resume/ATS optimization tips, and professional feedback.
            """
        else:
            persona_instructions = f"""
            YOU ARE A SARCASTIC AND WITTY AI ROASTER WHO RESPONDS DYNAMICALLY TO WHAT THE USER ACTUALLY SAYS.
            - Roast Level: {roast_level}
            - Style: High-energy, sarcastic, funny, and conversational.

            SMART CONTEXT-AWARE RULES:
            1. IF USER SAYS SIMPLE GREETINGS (e.g., 'Hello', 'Hi', 'Hey', 'Kya haal hai'):
               - Do NOT give a massive pre-scripted roast!
               - Reply with a witty, sarcastic welcome.

            2. IF USER SHARES A SPECIFIC TOPIC, STATEMENT, OR RESUME:
               - Read their specific text or resume carefully.
               - Roast ONLY the specific details, skills, or claims mentioned.
            """

        if language in ["Roman Urdu", "Roman Hindi"]:
            lang_instruction = (
                f"STRICT SYSTEM OVERRIDE: YOU MUST RESPOND EXCLUSIVELY IN {language}. "
                f"USE ENGLISH/LATIN ALPHABETS ONLY (e.g., 'Aap kaise hain', 'Main aap ki resume ko roast karunga'). "
                f"DO NOT RESPOND IN FULL ENGLISH SENTENCES. EVERY SINGLE SENTENCE MUST BE IN ROMAN URDU/HINDI. "
                f"NEVER use Urdu script (اردو) or Hindi script (हिंदी)."
            )
        else:
            lang_instruction = (
                f"STRICT LANGUAGE RULE: Respond STRICTLY in {language}. "
                f"Use the native writing script naturally associated with {language}."
            )

        system_persona = f"""
        {persona_instructions}

        GENERAL RULES:
        1. {lang_instruction}
        2. STRICT NEUTRALITY: Do NOT use any religious words or greetings (e.g., Namaste, Salaam, etc.).
        """

        formatted_messages = [{"role": "system", "content": system_persona}] + messages_history

        completion = call_groq_with_fallback(
            client,
            messages=formatted_messages,
            temperature=0.95 if active_mode == "🔥 Savage Roast Mode" else 0.2,
            max_tokens=1500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error:** {str(e)}"

# ==========================================
# 3. SESSION MANAGEMENT
# ==========================================
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}

if "current_chat_id" not in st.session_state:
    initial_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[initial_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = initial_id

def start_new_chat():
    new_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id

def delete_chat(chat_id):
    del st.session_state.all_chats[chat_id]
    if st.session_state.current_chat_id == chat_id:
        if st.session_state.all_chats:
            st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
        else:
            start_new_chat()

current_id = st.session_state.current_chat_id
current_chat = st.session_state.all_chats[current_id]

# ==========================================
# 4. SIDEBAR CONTROLS & MONETIZATION
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='font-weight:700;'>⚙️ Settings</h3>", unsafe_allow_html=True)
    st.markdown("🟢 **Current Plan:** <span class='pro-badge' style='background-color:#1F6FEB;'>Free Mode</span>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background-color:#161B22; border:1px solid #30363D; border-radius:8px; padding:12px; margin:10px 0;">
            <p style="margin:0; font-size:0.85rem; color:#8B949E;">Want unlimited high-speed AI responses & priority servers?</p>
            <a href="https://ai-roaster.lemonsqueezy.com" target="_blank" style="text-decoration:none;">
                <button style="width:100%; margin-top:8px; background-color:#238636; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer; font-weight:bold;">
                    ⚡ Upgrade to Pro
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

    language = st.selectbox(
        "Response Language:",
        [
            "Roman Urdu", 
            "Roman Hindi", 
            "English", 
            "Urdu (اردو)", 
            "Hindi (हिंदी)", 
            "Spanish (Español)", 
            "French (Français)", 
            "German (Deutsch)", 
            "Arabic (العربية)", 
            "Turkish (Türkçe)", 
            "Chinese (中文)", 
            "Japanese (日本語)"
        ]
    )

    st.markdown("---")
    st.markdown("<h4>🎯 AI Persona</h4>", unsafe_allow_html=True)
    active_mode = st.radio(
        "Select Persona:",
        ["🔥 Savage Roast Mode", "🧠 Thinking & Career Assistant"]
    )

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roast Mode":
        st.markdown("<h4>🌶️ Roast Intensity</h4>", unsafe_allow_html=True)
        roast_level = st.select_slider(
            "Level:",
            options=["Normal", "Medium", "Hard"],
            value="Medium"
        )

    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("<h5 style='margin-top: 15px; color:#8B949E;'>Recent Sessions</h5>", unsafe_allow_html=True)
    
    for c_id in list(st.session_state.all_chats.keys())[::-1]:
        chat_info = st.session_state.all_chats[c_id]
        col_btn, col_del = st.columns([4.2, 0.8])
        
        is_active = "💬 " if c_id == st.session_state.current_chat_id else ""
        btn_label = f"{is_active}{chat_info['title']}"
        
        if col_btn.button(btn_label, key=f"btn_{c_id}", use_container_width=True):
            st.session_state.current_chat_id = c_id
            st.rerun()
            
        if col_del.button("🗑️", key=f"del_{c_id}"):
            delete_chat(c_id)
            st.rerun()

# ==========================================
# 5. MAIN INTERFACE
# ==========================================
st.markdown("""
    <div class='brand-header'>
        <h1 class='brand-title'>AI Roaster & Career Assistant</h1>
        <p class='brand-subtitle'>Chat casually or attach files directly in one smart input bar.</p>
    </div>
""", unsafe_allow_html=True)

if not current_chat["messages"]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class='mode-card'>
                <h4>🔥 Savage Roast Mode</h4>
                <p>Attach a resume PDF or chat directly for sharp, witty, and honest feedback.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='mode-card'>
                <h4>🧠 Career Assistant Mode</h4>
                <p>Get ATS breakdowns, career guidance, and actionable tech tips.</p>
            </div>
        """, unsafe_allow_html=True)

# Render Chat History
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# INTEGRATED CHAT INPUT BAR
chat_input_data = st.chat_input(
    f"Type a message or attach PDF... ({active_mode})",
    accept_file=True,
    file_type=["pdf"]
)

if chat_input_data:
    prompt_text = chat_input_data.get("text", "")
    uploaded_files = chat_input_data.get("files", [])
    
    combined_user_content = ""
    file_context = ""

    if uploaded_files:
        pdf_file = uploaded_files[0]
        extracted_text = read_pdf(pdf_file)
        if extracted_text:
            file_context = f"\n\n--- [ATTACHED RESUME CONTENT: {pdf_file.name}] ---\n{extracted_text}"
            st.toast(f"📄 Attached: {pdf_file.name}", icon="✅")

    if prompt_text and file_context:
        combined_user_content = f"{prompt_text}\n{file_context}"
        user_display_msg = f"📎 **[Attached Resume: {uploaded_files[0].name}]**\n\n{prompt_text}"
    elif file_context:
        combined_user_content = f"Evaluate my attached resume.\n{file_context}"
        user_display_msg = f"📎 **[Attached Resume: {uploaded_files[0].name}]**\nPlease evaluate my resume."
    else:
        combined_user_content = prompt_text
        user_display_msg = prompt_text

    # Auto-generate Title for New Chat Session
    if not current_chat["messages"] or current_chat["title"] == "New Chat":
        sample_text = prompt_text if prompt_text else (uploaded_files[0].name if uploaded_files else "Conversation")
        generated_title = generate_chat_title(sample_text)
        current_chat["title"] = generated_title

    st.chat_message("user").markdown(user_display_msg)
    current_chat["messages"].append({"role": "user", "content": combined_user_content})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_ai_response(
                current_chat["messages"],
                active_mode,
                roast_level,
                language
            )
            st.markdown(response)
            current_chat["messages"].append({"role": "assistant", "content": response})

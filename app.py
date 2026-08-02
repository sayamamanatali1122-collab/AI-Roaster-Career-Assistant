import os
import datetime
import streamlit as st
from pypdf import PdfReader
from groq import Groq

# Constants
PAGE_TITLE = "AI Roaster & Career Assistant"
PAGE_ICON = "🤖"
LAYOUT = "wide"

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# ⚡ CLEAN MODERN STYLING (Sidebar Toggle Restored)
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #0D1117 !important;
        color: #C9D1D9 !important;
    }

    /* Professional Dark Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B22 !important;
        border-right: 1px solid #30363D !important;
    }

    /* Highlight Official Sidebar Collapse/Expand Button */
    [data-testid="stSidebarCollapseButton"], 
    [data-testid="stSidebarExpandButton"] {
        background-color: #21262D !important;
        color: #58A6FF !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        padding: 4px !important;
        margin-top: 8px !important;
        margin-left: 8px !important;
    }

    /* Hide Unwanted Header/Footer Elements without hiding Toggle Arrow */
    #MainMenu, footer, [data-testid="stDecoration"], 
    [data-testid="stStatusWidget"], div[class*="ViewerBadge"] {
        display: none !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Layout Spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 6rem !important;
        max-width: 950px !important;
        margin: 0 auto;
    }

    /* High Contrast Text Labels */
    label, [data-testid="stWidgetLabel"] {
        color: #F0F6FC !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    /* Header Styling */
    .brand-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .brand-title {
        font-size: clamp(1.8rem, 4vw, 2.5rem) !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
    }
    
    .brand-subtitle {
        color: #8B949E !important;
        font-size: 1rem !important;
        margin-top: 6px;
    }

    /* Cards */
    .mode-card {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 12px;
        height: 100%;
    }
    
    .mode-card h4 {
        color: #FFFFFF !important;
        font-size: 1.05rem !important;
        font-weight: 700;
        margin: 0 0 6px 0;
    }
    
    .mode-card p {
        color: #8B949E !important;
        font-size: 0.88rem !important;
        margin: 0;
    }

    /* Bottom Chat Input Fix */
    [data-testid="stChatInput"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 10px !important;
    }
</style>
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
# 4. SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid #30363D; padding-bottom:10px;">
            <span style="font-size:1.5rem;">🤖</span>
            <h3 style="margin:0; color:#FFFFFF; font-size:1.15rem;">AI Assistant</h3>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("🟢 **Status:** <span style='background:#1F6FEB; color:#FFF; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>Free Plan</span>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background-color:#0D1117; border:1px solid #30363D; border-radius:8px; padding:10px; margin:10px 0;">
            <p style="margin:0; font-size:0.8rem; color:#8B949E;">Upgrade for unlimited speed & priority AI models.</p>
            <a href="https://airoaster.lemonsqueezy.com/checkout/buy/ec7ff9c8-e11c-4102-aa52-3f5884f8fb2c" target="_blank" style="text-decoration:none;">
                <button style="width:100%; margin-top:8px; background-color:#238636; color:white; border:none; padding:6px; border-radius:6px; cursor:pointer; font-weight:bold; font-size:0.85rem;">
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
    active_mode = st.radio(
        "AI MODE:",
        ["🔥 Savage Roast Mode", "🧠 Thinking & Career Assistant"]
    )

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roast Mode":
        roast_level = st.select_slider(
            "ROAST INTENSITY:",
            options=["Normal", "Medium", "Hard"],
            value="Medium"
        )

    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("<p style='margin-top:10px; color:#8B949E; font-size:0.8rem; font-weight:600;'>RECENT CHATS</p>", unsafe_allow_html=True)
    
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
        <p class='brand-subtitle'>Chat casually or attach PDF files directly for sharp AI analysis.</p>
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
                <p>Get ATS breakdowns, professional career guidance, and actionable tech advice.</p>
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

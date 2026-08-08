import os
import datetime
import requests
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

# ⚡ CLEAN MODERN STYLING
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

    /* Layout Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
        max-width: 900px !important;
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
        margin-bottom: 1.5rem;
    }
    
    .brand-title {
        font-size: clamp(1.8rem, 4vw, 2.5rem) !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
    }
    
    .brand-subtitle {
        color: #8B949E !important;
        font-size: 0.95rem !important;
        margin-top: 4px;
    }

    /* Cards */
    .mode-card {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .mode-card h4 {
        color: #FFFFFF !important;
        font-size: 1rem !important;
        font-weight: 700;
        margin: 0 0 4px 0;
    }
    
    .mode-card p {
        color: #8B949E !important;
        font-size: 0.85rem !important;
        margin: 0;
    }

    /* Input & Upload Box styling */
    [data-testid="stFileUploader"] {
        background-color: #161B22 !important;
        border: 1px dashed #30363D !important;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE INIT
# ==========================================
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}

if "current_chat_id" not in st.session_state:
    initial_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[initial_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = initial_id

if "pending_pdf_text" not in st.session_state:
    st.session_state.pending_pdf_text = None
if "pending_pdf_name" not in st.session_state:
    st.session_state.pending_pdf_name = None

# ==========================================
# 3. HELPER FUNCTIONS & AI ENGINE
# ==========================================
def read_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip() if text.strip() else None
    except Exception as e:
        st.error(f"PDF parhne mein masla hua: {e}")
        return None

def get_effective_api_key():
    try:
        if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")

def verify_lemonsqueezy_license(license_key):
    url = "https://api.lemonsqueezy.com/v1/licenses/validate"
    payload = {"license_key": license_key.strip()}
    try:
        response = requests.post(url, data=payload, timeout=10)
        data = response.json()
        if data.get("valid", False):
            return True, "License successfully verified!"
        else:
            return False, data.get("error", "Invalid license key.")
    except Exception as e:
        return False, f"Verification error: {str(e)}"

# ⚡ Groq Call with Frequency & Presence Penalty to stop repetitions
def call_groq_with_fallback(client, messages, temperature=0.7, max_tokens=1000, is_pro=False):
    primary_model = "llama-3.3-70b-versatile" if is_pro else "llama-3.1-8b-instant"
    fallback_model = "llama-3.1-8b-instant"

    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "frequency_penalty": 0.6,  # Prevents repeating same words
        "presence_penalty": 0.6,   # Encourages new topics/phrases
    }

    try:
        return client.chat.completions.create(model=primary_model, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "rate_limit" in error_msg or "tokens" in error_msg:
            return client.chat.completions.create(model=fallback_model, **kwargs)
        raise e

def generate_chat_title(first_user_msg):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "New Chat"
    try:
        client = Groq(api_key=effective_key)
        prompt = f"Summarize this input into a short 2 to 4 word chat title: '{first_user_msg[:150]}'"
        completion = call_groq_with_fallback(
            client, 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=15,
            is_pro=st.session_state.is_pro
        )
        title = completion.choices[0].message.content.strip().replace('"', '')
        return title[:25]
    except Exception:
        cleaned = first_user_msg.strip().split("\n")[0]
        return cleaned[:20] + "..." if len(cleaned) > 20 else cleaned

def get_ai_response(messages_history, active_mode, roast_level, language):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "⚠️ **Error:** GROQ_API_KEY missing hai!"

    try:
        client = Groq(api_key=effective_key)

        if active_mode == "🧠 Thinking & Career Assistant":
            persona_instructions = """
            YOU ARE A HIGHLY PROFESSIONAL CAREER & ATS RESUME EXPERT.
            - Tone: Encouraging, objective, professional, and clear.
            - DO NOT roast or insult. Provide constructive resume tips, ATS score improvements, and actionable advice.
            """
        else:
            intensity_map = {
                "Normal": "Funny, sarcastic, lighthearted banter.",
                "Medium": "Sharp, brutally honest, witty roast.",
                "Hard": "ULTIMATE SAVAGE ROAST! Ruthlessly target weak points, buzzwords, and experience gaps."
            }
            persona_instructions = f"""
            YOU ARE AN UNFILTERED, HILARIOUS, AND WITTY AI ROASTER.
            Roast Level: {roast_level} ({intensity_map.get(roast_level, 'Sharp roast')})

            RULES FOR ROASTING:
            1. PUNCHY & CONCISE: Keep response between 120-250 words max. Never write boring walls of text.
            2. TARGET SPECIFIC DETAILS: Read the user's text or resume carefully and roast specific skills, projects, gaps, or buzzwords.
            3. NO REPETITION: Do NOT repeat previous jokes, phrases, or greetings.
            4. QUICK BANTER: If user just says 'Hi/Hello', give a quick 2-line sarcastic greeting.
            """

        if language in ["Roman Urdu", "Roman Hindi"]:
            lang_instruction = (
                f"STRICT LANGUAGE RULE: Respond EXCLUSIVELY in {language} (Latin/English script). "
                f"Example: 'Aapki resume dekh kar lagta hai aap ne MS Word ke saare templates try kar liye hain.' "
                f"DO NOT write in English sentences or Urdu/Hindi scripts."
            )
        else:
            lang_instruction = f"STRICT LANGUAGE RULE: Respond strictly in {language}."

        system_persona = f"""
        {persona_instructions}
        {lang_instruction}
        STRICT NEUTRALITY: Do NOT use religious greetings (e.g., Namaste, Salaam, etc.).
        """

        formatted_messages = [{"role": "system", "content": system_persona}] + messages_history[-6:]  # Keep context fresh

        completion = call_groq_with_fallback(
            client,
            messages=formatted_messages,
            temperature=0.85 if active_mode == "🔥 Savage Roast Mode" else 0.3,
            max_tokens=900,
            is_pro=st.session_state.is_pro
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error:** {str(e)}"

def start_new_chat():
    new_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id
    st.session_state.pending_pdf_text = None
    st.session_state.pending_pdf_name = None

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
# 4. SIDEBAR CONTROLS & LICENSE
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; border-bottom:1px solid #30363D; padding-bottom:10px;">
            <span style="font-size:1.5rem;">🤖</span>
            <h3 style="margin:0; color:#FFFFFF; font-size:1.1rem;">AI Assistant</h3>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.is_pro:
        st.markdown("🔥 **Status:** <span style='background:#238636; color:#FFF; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>Pro Active</span>", unsafe_allow_html=True)
    else:
        st.markdown("🟢 **Status:** <span style='background:#1F6FEB; color:#FFF; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>Free Plan</span>", unsafe_allow_html=True)
        with st.expander("🔑 Activate Pro License"):
            license_input = st.text_input("Lemon Squeezy License Key:", type="password")
            if st.button("Activate"):
                if license_input:
                    valid, msg = verify_lemonsqueezy_license(license_input)
                    if valid:
                        st.session_state.is_pro = True
                        st.success("Pro Activated!")
                        st.rerun()
                    else:
                        st.error(msg)

    language = st.selectbox(
        "Response Language:",
        ["Roman Urdu", "Roman Hindi", "English", "Urdu (اردو)", "Hindi (हिंदी)", "Spanish", "French", "German", "Arabic", "Turkish"]
    )

    st.markdown("---")
    active_mode = st.radio("AI MODE:", ["🔥 Savage Roast Mode", "🧠 Thinking & Career Assistant"])

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roast Mode":
        roast_level = st.select_slider("ROAST INTENSITY:", options=["Normal", "Medium", "Hard"], value="Medium")

    st.markdown("---")
    
    # 📱 MOBILE FRIENDLY DEDICATED PDF UPLOADER IN SIDEBAR / MAIN
    st.markdown("📄 **Upload Resume PDF (Mobile Friendly):**")
    uploaded_pdf = st.file_uploader("Select Resume PDF", type=["pdf"], key="sidebar_pdf")
    if uploaded_pdf:
        pdf_text = read_pdf(uploaded_pdf)
        if pdf_text:
            st.session_state.pending_pdf_text = pdf_text
            st.session_state.pending_pdf_name = uploaded_pdf.name
            st.success(f"✅ Loaded: {uploaded_pdf.name}")

    st.markdown("---")
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("<p style='margin-top:10px; color:#8B949E; font-size:0.8rem;'>RECENT CHATS</p>", unsafe_allow_html=True)
    for c_id in list(st.session_state.all_chats.keys())[::-1]:
        chat_info = st.session_state.all_chats[c_id]
        col_btn, col_del = st.columns([4.2, 0.8])
        is_active = "💬 " if c_id == st.session_state.current_chat_id else ""
        if col_btn.button(f"{is_active}{chat_info['title']}", key=f"btn_{c_id}", use_container_width=True):
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
        <p class='brand-subtitle'>Chat casually or attach PDF resume for instant AI analysis.</p>
    </div>
""", unsafe_allow_html=True)

if not current_chat["messages"]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class='mode-card'>
                <h4>🔥 Savage Roast Mode</h4>
                <p>Upload a resume or chat directly for sharp, witty, and honest feedback.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='mode-card'>
                <h4>🧠 Career Assistant Mode</h4>
                <p>Get ATS breakdowns, professional career guidance, and actionable advice.</p>
            </div>
        """, unsafe_allow_html=True)

# Render Chat History
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input Bar (Handles text input)
prompt_text = st.chat_input(f"Type a message... ({active_mode})")

if prompt_text or st.session_state.pending_pdf_text:
    user_text = prompt_text if prompt_text else "Please evaluate my uploaded resume."
    
    file_context = ""
    user_display_msg = user_text

    if st.session_state.pending_pdf_text:
        pdf_name = st.session_state.pending_pdf_name
        file_context = f"\n\n--- [ATTACHED RESUME CONTENT: {pdf_name}] ---\n{st.session_state.pending_pdf_text}"
        user_display_msg = f"📎 **[Attached Resume: {pdf_name}]**\n\n{user_text}"
        # Reset pending PDF after attaching
        st.session_state.pending_pdf_text = None
        st.session_state.pending_pdf_name = None

    combined_user_content = f"{user_text}{file_context}"

    # Auto Title Generator
    if not current_chat["messages"] or current_chat["title"] == "New Chat":
        current_chat["title"] = generate_chat_title(user_text)

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

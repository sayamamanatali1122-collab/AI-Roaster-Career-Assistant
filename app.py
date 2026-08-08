import os
import datetime
import requests
import streamlit as st
from pypdf import PdfReader
from groq import Groq

# Constants
PAGE_TITLE = "Advanced AI Companion & Career Assistant"
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
        padding-bottom: 6rem !important;
        max-width: 920px !important;
        margin: 0 auto;
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
        height: 100%;
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

    /* Gemini Bar Attachment Button */
    div[data-testid="stPopover"] > button {
        background-color: #21262D !important;
        color: #58A6FF !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
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

if "attached_pdf_text" not in st.session_state:
    st.session_state.attached_pdf_text = None
if "attached_pdf_name" not in st.session_state:
    st.session_state.attached_pdf_name = None

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
        st.error(f"PDF reading error: {e}")
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

def call_groq_with_fallback(client, messages, temperature=0.7, max_tokens=1000, is_pro=False):
    primary_model = "llama-3.3-70b-versatile" if is_pro else "llama-3.1-8b-instant"
    fallback_model = "llama-3.1-8b-instant"

    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "frequency_penalty": 0.6,
        "presence_penalty": 0.6,
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
        prompt = f"Summarize this input into a short 2 to 4 word title: '{first_user_msg[:150]}'"
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

def get_ai_response(messages_history, active_mode, roast_level, language, active_pdf_text=None):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "⚠️ **Error:** GROQ_API_KEY missing hai!"

    try:
        client = Groq(api_key=effective_key)

        # Detect last user message intent
        last_user_msg = ""
        for m in reversed(messages_history):
            if m["role"] == "user":
                last_user_msg = m["content"].strip().lower()
                break

        greetings_list = ["hi", "hello", "hey", "hy", "hlo", "assalamoalaikum", "salam", "kya haal hai", "kaise ho", "good morning", "good evening"]
        words = last_user_msg.split()
        is_greeting = (last_user_msg in greetings_list) or (len(words) <= 3 and any(g in last_user_msg for g in ["hi", "hello", "hey", "salam", "kaise", "haal"]))
        is_asking_about_bot = any(w in last_user_msg for w in ["tum kon ho", "tumhare kya feature", "tum kya kar sakte ho", "features", "who are you", "what can you do"])

        if active_mode == "🌟 Versatile AI Companion":
            if is_asking_about_bot:
                persona_instructions = """
                YOU ARE AN ADVANCED MULTI-MODAL AI COMPANION (LIKE CHATGPT & GEMINI).
                User is asking about your capabilities. Explain clearly that you can help with:
                1. 💬 General Q&A, Discussions & Brainstorming
                2. 💻 Coding, Debugging & Scripting
                3. 📄 Resume Evaluation & PDF Analysis
                4. 🔥 Savage Resume/Code Roasting (Optional Mode)
                5. 🧠 Career Guidance & ATS Optimization
                """
            elif is_greeting:
                persona_instructions = """
                YOU ARE A WARM, INTELLIGENT, AND FRIENDLY ADVANCED AI COMPANION.
                Greet the user warmly, politely, and naturally. Ask how you can assist them today.
                """
            else:
                persona_instructions = """
                YOU ARE AN ADVANCED AI ASSISTANT (LIKE CHATGPT & GEMINI).
                Respond intelligently, helpfully, and accurately to any user request (Coding, Q&A, Writing, etc.).
                """

        elif active_mode == "🧠 Career & ATS Expert":
            persona_instructions = """
            YOU ARE A PROFESSIONAL CAREER & ATS RESUME EXPERT.
            - Provide structured, professional advice, ATS resume scoring tips, and constructive recommendations.
            """

        else: # 🔥 Savage Roast Mode
            intensity_map = {
                "Normal": "Funny, sarcastic, lighthearted banter.",
                "Medium": "Sharp, brutally honest, witty roast.",
                "Hard": "ULTIMATE SAVAGE ROAST! Ruthlessly target weak points, buzzwords, and experience gaps."
            }

            if is_greeting and not active_pdf_text:
                persona_instructions = f"""
                YOU ARE A WITTY, QUICK-THINKING AI ROASTER.
                User sent a simple greeting ('{last_user_msg}'). NO RESUME IS ATTACHED.
                STRICT RULES:
                1. Reply with a fun, witty, sarcastic greeting!
                2. Ask what they want to roast today (e.g., 'Haan ji! Aaj kya roast karwana hai?').
                3. DO NOT force 'The Roast' or 'How to Fix' headers for a simple greeting!
                """
            elif active_pdf_text:
                persona_instructions = f"""
                YOU ARE AN INTELLIGENT AI ROASTER & CAREER CONSULTANT.
                Roast Level: {roast_level} ({intensity_map.get(roast_level, 'Sharp roast')})
                A RESUME PDF HAS BEEN ATTACHED.
                Structure your response into 2 distinct sections:
                1. 🔥 **The Roast:** Witty, sarcastic, sharp attack on actual weak points, gaps, or buzzwords in the attached resume.
                2. 💡 **How to Fix It (Solution):** 2-3 clear, professional, actionable steps to fix those exact weaknesses.
                """
            else:
                persona_instructions = f"""
                YOU ARE AN INTELLIGENT AI ROASTER.
                Roast Level: {roast_level} ({intensity_map.get(roast_level, 'Sharp roast')})
                User provided: '{last_user_msg}'.

                DYNAMIC THINKING RULES FOR ROASTING:
                1. IF USER IS PLAYING/BANTERING (e.g., 'tum mujhe roast karo main tumhein', jokes, playful banter):
                   - Roast them back with sharp, hilarious, witty banter!
                   - DO NOT add a preachy 'How to Fix It' section! DO NOT lecture them about 'professionalism' or 'self-awareness'!
                
                2. IF USER SHARED A SPECIFIC CODE, BUSINESS IDEA, OR ACTUAL RESUME/CAREER PROBLEM:
                   - Roast the specific idea/code.
                   - Provide a 💡 **How to Fix It (Solution)** section ONLY if there is a real technical/business problem to solve.
                """

        if language in ["Roman Urdu", "Roman Hindi"]:
            lang_instruction = f"""
            STRICT LANGUAGE & GRAMMAR RULES FOR {language}:
            1. Use NATURAL everyday spoken {language} in Latin script.
            2. STRICT GENDER RULE: Always address the user in standard masculine/neutral form ('kar rahe ho', 'puch rahe ho', 'aaye ho', 'kaise ho'). NEVER use wrong female inflections ('leti ho', 'kar rahi ho', 'aayi hai').
            3. NO BROKEN GOOGLE TRANSLATIONS: Write naturally like a real Pakistani/Indian tech user on WhatsApp.
            """
        else:
            lang_instruction = f"STRICT LANGUAGE RULE: Respond strictly in {language}."

        system_persona = f"""
        {persona_instructions}
        {lang_instruction}
        STRICT NEUTRALITY: Do NOT use religious greetings (e.g., Namaste, Salaam, etc.).
        """

        formatted_messages = [{"role": "system", "content": system_persona}]
        
        # Add past clean messages
        for msg in messages_history[-6:]:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        # Inject PDF text ONLY if evaluating PDF right now
        if active_pdf_text:
            formatted_messages.append({
                "role": "system",
                "content": f"ATTACHED RESUME CONTENT TO EVALUATE:\n{active_pdf_text}"
            })

        temp = 0.7 if (is_greeting or is_asking_about_bot) else (0.85 if active_mode == "🔥 Savage Roast Mode" else 0.4)

        completion = call_groq_with_fallback(
            client,
            messages=formatted_messages,
            temperature=temp,
            max_tokens=950,
            is_pro=st.session_state.is_pro
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error:** {str(e)}"

def start_new_chat():
    new_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id
    st.session_state.attached_pdf_text = None
    st.session_state.attached_pdf_name = None

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
            <h3 style="margin:0; color:#FFFFFF; font-size:1.1rem;">AI Companion</h3>
        </div>
    """, unsafe_allow_html=True)

    # Status Display
    if st.session_state.is_pro:
        st.markdown("🔥 **Status:** <span style='background:#238636; color:#FFF; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>Pro Active</span>", unsafe_allow_html=True)
    else:
        st.markdown("🟢 **Status:** <span style='background:#1F6FEB; color:#FFF; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>Free Plan</span>", unsafe_allow_html=True)
        
        st.markdown("""
            <div style="background-color:#0D1117; border:1px solid #30363D; border-radius:8px; padding:10px; margin:10px 0;">
                <p style="margin:0; font-size:0.8rem; color:#8B949E;">Upgrade for unlimited speed & priority AI models.</p>
                <a href="https://airoaster.lemonsqueezy.com/checkout/buy/ec7ff9c8-e11c-4102-aa52-3f5884f8fb2c" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; margin-top:8px; background-color:#238636; color:white; border:none; padding:6px; border-radius:6px; cursor:pointer; font-weight:bold; font-size:0.85rem;">
                        ⚡ Upgrade to Pro ($6)
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🔑 Already paid? Activate License"):
            license_input = st.text_input("Lemon Squeezy License Key:", type="password")
            if st.button("Activate Pro"):
                if license_input:
                    valid, msg = verify_lemonsqueezy_license(license_input)
                    if valid:
                        st.session_state.is_pro = True
                        st.success("Pro Activated!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter a valid key.")

    # DEVELOPER ACCESS SECTION
    with st.expander("🛠️ Developer Access"):
        if st.session_state.is_pro:
            st.info("⚡ You are currently in **Dev Pro Mode**.")
            if st.button("🔴 Deactivate Dev Mode", use_container_width=True):
                st.session_state.is_pro = False
                st.success("Switched to Free Mode!")
                st.rerun()
        else:
            entered_key = st.text_input("Enter Secret Key", type="password", key="dev_key_input")
            if st.button("🔓 Activate Dev Pro", use_container_width=True):
                dev_secret = None
                try:
                    if "DEV_SECRET_KEY" in st.secrets and st.secrets["DEV_SECRET_KEY"]:
                        dev_secret = st.secrets["DEV_SECRET_KEY"]
                except Exception:
                    pass

                if not dev_secret:
                    st.error("❌ DEV_SECRET_KEY is not configured in st.secrets!")
                elif entered_key and entered_key == dev_secret:
                    st.session_state.is_pro = True
                    st.success("🎉 Dev Pro Mode Activated Successfully!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Secret Key!")

    language = st.selectbox(
        "Response Language:",
        ["Roman Urdu", "Roman Hindi", "English", "Urdu (اردو)", "Hindi (हिंदी)", "Spanish", "French", "German", "Arabic", "Turkish"]
    )

    st.markdown("---")
    active_mode = st.radio(
        "AI MODE:", 
        ["🌟 Versatile AI Companion", "🔥 Savage Roast Mode", "🧠 Career & ATS Expert"]
    )

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roast Mode":
        roast_level = st.select_slider("ROAST INTENSITY:", options=["Normal", "Medium", "Hard"], value="Medium")

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
        <h1 class='brand-title'>Advanced AI Companion</h1>
        <p class='brand-subtitle'>Chat casually, ask questions, generate code, or attach PDF resume for smart analysis.</p>
    </div>
""", unsafe_allow_html=True)

if not current_chat["messages"]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class='mode-card'>
                <h4>🌟 Versatile AI (ChatGPT/Gemini)</h4>
                <p>Ask anything, generate code, write emails, or chat casually with smart AI.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='mode-card'>
                <h4>🔥 Savage Roast Mode</h4>
                <p>Upload a resume or text for sharp, witty roasts + actionable solutions.</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class='mode-card'>
                <h4>🧠 Career & ATS Expert</h4>
                <p>Get ATS breakdowns, interview prep, and professional career advice.</p>
            </div>
        """, unsafe_allow_html=True)

# Render Chat History
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 📎 GEMINI-STYLE ATTACHMENT BAR RIGHT ABOVE CHAT INPUT
col_attach, col_status = st.columns([1.2, 3.8])
with col_attach:
    with st.popover("📎 Attach PDF"):
        file_input = st.file_uploader("Upload Resume PDF", type=["pdf"], key="main_pdf_uploader")
        if file_input:
            p_text = read_pdf(file_input)
            if p_text:
                st.session_state.attached_pdf_text = p_text
                st.session_state.attached_pdf_name = file_input.name
                st.success(f"Loaded: {file_input.name}")

with col_status:
    if st.session_state.attached_pdf_name:
        st.markdown(f"📄 **Attached:** `{st.session_state.attached_pdf_name}`")

# Chat Input Bar
prompt_text = st.chat_input(f"Type a message... ({active_mode})")

if prompt_text or st.session_state.attached_pdf_text:
    user_text = prompt_text if prompt_text else "Please evaluate my attached resume."
    
    current_pdf_text = st.session_state.attached_pdf_text
    user_display_msg = user_text

    if st.session_state.attached_pdf_name and current_pdf_text:
        user_display_msg = f"📎 **[Attached Resume: {st.session_state.attached_pdf_name}]**\n\n{user_text}"
        # Consume the attachment so it doesn't leak into future turns
        st.session_state.attached_pdf_text = None
        st.session_state.attached_pdf_name = None

    # Auto Title Generator
    if not current_chat["messages"] or current_chat["title"] == "New Chat":
        current_chat["title"] = generate_chat_title(user_text)

    st.chat_message("user").markdown(user_display_msg)
    current_chat["messages"].append({"role": "user", "content": user_display_msg})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_ai_response(
                current_chat["messages"],
                active_mode,
                roast_level,
                language,
                active_pdf_text=current_pdf_text
            )
            st.markdown(response)
            current_chat["messages"].append({"role": "assistant", "content": response})

import os
import datetime
import requests
import base64
import io
import streamlit as st
from pypdf import PdfReader
from PIL import Image
from groq import Groq

# Constants
PAGE_TITLE = "Advanced AI Companion & Multimodal Assistant"
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

# ⚡ CLEAN CHATGPT / GEMINI OFFICIAL STYLING
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
        max-width: 900px !important;
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

    /* PERFECT EQUAL HEIGHT CARDS */
    .mode-card {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px;
        padding: 18px;
        min-height: 140px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        transition: border-color 0.2s ease;
    }
    .mode-card:hover {
        border-color: #58A6FF !important;
    }
    
    .mode-card h4 {
        color: #FFFFFF !important;
        font-size: 1rem !important;
        font-weight: 700;
        margin: 0 0 6px 0;
    }
    
    .mode-card p {
        color: #8B949E !important;
        font-size: 0.86rem !important;
        margin: 0;
        line-height: 1.4;
    }

    /* Clean Expander / Popover for File Attachment */
    [data-testid="stExpander"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 10px !important;
        margin-bottom: 10px !important;
    }

    /* Clean Chat Input Bar */
    div[data-testid="stChatInput"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 24px !important;
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

if "attached_file_data" not in st.session_state:
    st.session_state.attached_file_data = None
if "attached_file_name" not in st.session_state:
    st.session_state.attached_file_name = None
if "attached_file_type" not in st.session_state:
    st.session_state.attached_file_type = None

# ==========================================
# 3. MULTIMODAL FILE PROCESSOR & AI ENGINE
# ==========================================
def process_uploaded_file(uploaded_file):
    file_type = uploaded_file.type
    file_name = uploaded_file.name

    if "pdf" in file_type or file_name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return ("pdf", text.strip() if text.strip() else "PDF loaded, but text could not be extracted.")
        except Exception as e:
            return ("error", f"PDF Extraction Error: {str(e)}")

    elif any(img_ext in file_type or file_name.lower().endswith(img_ext) for img_ext in ["png", "jpg", "jpeg", "webp"]):
        try:
            image = Image.open(uploaded_file)
            buffered = io.BytesIO()
            img_format = "PNG" if file_name.lower().endswith(".png") else "JPEG"
            image.save(buffered, format=img_format)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return ("image", img_b64)
        except Exception as e:
            return ("error", f"Image Error: {str(e)}")

    return ("error", "Unsupported file type! Please upload a PDF or Image (PNG, JPG, JPEG).")

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

# ⚡ Groq Text & Multimodal Execution
def call_groq_engine(client, messages, is_pro=False, image_b64=None):
    primary_model = "llama-3.3-70b-versatile" if is_pro else "llama-3.1-8b-instant"
    fallback_model = "llama-3.1-8b-instant"
    vision_model = "llama-3.2-11b-vision-instruct"

    # Multimodal Vision Execution for Images
    if image_b64:
        try:
            text_prompt = "\n".join([m.get("content", "") for m in messages if isinstance(m.get("content"), str)])
            vision_messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ]
            return client.chat.completions.create(
                model=vision_model,
                messages=vision_messages,
                max_tokens=1000,
                temperature=0.7
            )
        except Exception:
            pass

    # Standard Text Execution
    kwargs = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
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
        completion = call_groq_engine(
            client, 
            messages=[{"role": "user", "content": prompt}],
            is_pro=st.session_state.is_pro
        )
        title = completion.choices[0].message.content.strip().replace('"', '')
        return title[:25]
    except Exception:
        cleaned = first_user_msg.strip().split("\n")[0]
        return cleaned[:20] + "..." if len(cleaned) > 20 else cleaned

def get_ai_response(messages_history, active_mode, roast_level, language, active_file_type=None, active_file_data=None):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "⚠️ **Error:** GROQ_API_KEY missing hai! Please secrets configuration check karein."

    try:
        client = Groq(api_key=effective_key)

        last_user_msg = ""
        for m in reversed(messages_history):
            if m["role"] == "user":
                last_user_msg = m["content"].strip().lower()
                break

        greetings_list = ["hi", "hello", "hey", "hy", "hlo", "assalamoalaikum", "salam", "kya haal hai", "kaise ho", "aao kaise ho", "good morning", "good evening"]
        words = last_user_msg.split()
        is_greeting = (last_user_msg in greetings_list) or (len(words) <= 3 and any(g in last_user_msg for g in ["hi", "hello", "hey", "salam", "kaise", "haal"]))
        is_asking_about_bot = any(w in last_user_msg for w in ["tum kon ho", "tumhare kya feature", "tum kya kar sakte ho", "features", "who are you", "what can you do"])

        if active_mode == "🌟 Versatile Assistant":
            if is_asking_about_bot:
                persona_instructions = """
                YOU ARE AN ADVANCED MULTI-MODAL AI COMPANION (LIKE CHATGPT & GEMINI).
                User is asking about your capabilities. Explain clearly that you can help with:
                1. 💬 General Q&A, Discussions & Brainstorming
                2. 💻 Coding, Debugging & Deep Logic Architecture
                3. 📄 PDF & Image Document Analysis (Multimodal Vision)
                4. 🔥 Savage Resume/Code/Topic Roasting (Optional Mode)
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
                Respond intelligently, helpfully, and accurately to any user request (Coding, Q&A, Writing, Image Analysis, etc.).
                """

        elif active_mode == "🧠 Career Expert":
            persona_instructions = """
            YOU ARE A PROFESSIONAL CAREER & ATS RESUME EXPERT.
            - Provide structured, professional advice, ATS resume scoring tips, and constructive recommendations.
            """

        else: # 🔥 Savage Roaster Mode
            intensity_map = {
                "Normal": "Funny, sarcastic, lighthearted banter.",
                "Medium": "Sharp, brutally honest, witty roast.",
                "Hard": "ULTIMATE HIGH-LEVEL SAVAGE ROAST! Ruthlessly target weak points, buzzwords, and funny traits like a top stand-up comedian."
            }

            if is_greeting and not active_file_data:
                persona_instructions = f"""
                YOU ARE A WITTY, HIGH-ENERGY DESI STAND-UP COMEDIAN ROASTER.
                User sent a simple greeting ('{last_user_msg}'). NO FILE IS ATTACHED.
                STRICT RULES:
                1. Reply with a fun, witty, sarcastic greeting in natural Pakistani Roman Urdu!
                2. Ask what they want to roast today (e.g., 'Haan ji! Aaj kis ko roast karwana hai — Donald Trump, koi bad idea, ganda code, ya koi Document/Resume attach kar rahe ho?').
                3. DO NOT force 'The Roast' or 'How to Fix' headers for a simple greeting!
                """
            elif active_file_data:
                persona_instructions = f"""
                YOU ARE AN INTELLIGENT AI ROASTER & CAREER CONSULTANT.
                Roast Level: {roast_level} ({intensity_map.get(roast_level, 'Sharp roast')})
                A DOCUMENT/RESUME FILE (PDF or IMAGE) HAS BEEN ATTACHED.
                Structure your response into 2 distinct sections:
                1. 🔥 **The Roast:** Witty, sarcastic, sharp attack on actual weak points, gaps, or buzzwords in the attached document.
                2. 💡 **How to Fix It (Solution):** 2-3 clear, professional, actionable steps to fix those exact weaknesses.
                """
            else:
                persona_instructions = f"""
                YOU ARE A SAVAGE, HIGH-ENERGY DESI ROASTER.
                Roast Level: {roast_level} ({intensity_map.get(roast_level, 'Sharp roast')})
                User requested to roast: '{last_user_msg}'.

                ROASTING EXECUTION RULES:
                1. REAL SAVAGE ROAST: Give hilarious, witty, punchy roast commentary on the target!
                2. NO GIBBERISH / NO FAKE DIALOGUES: DO NOT write fake scripted Q&A dialogues ('Trump: ... Tum: ...') and DO NOT use alien meaningless words.
                3. NO PREACHY LECTURES: DO NOT add a 'How to Fix It' or 'Solution' section unless a real technical/career bug or document is provided!
                """

        if language in ["Roman Urdu", "Roman Hindi"]:
            lang_instruction = f"""
            STRICT SIMPLE & NATURAL ROMAN URDU RULES:
            1. Use 100% SIMPLE, NATURAL everyday Pakistani Roman Urdu (e.g., 'Bhai', 'Yaar', 'Baat suno', 'Khas', 'Zaroori', 'Kya chal raha hai', 'Lagta hai').
            2. NO SHUDDH HINDI OR COMPLEX ENGLISH SLANG: NEVER use words like 'adarsh', 'vishesh', 'mehsus', 'avashyak', 'saari', 'karya', 'badaa' or confusing slang ('Orange Tan'). Use simple local terms everyone understands.
            3. PERFECT NATURAL GRAMMAR: Always address user in standard masculine/neutral form ('kar rahe ho', 'puch rahe ho', 'aaye ho', 'kaise ho').
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

        # Inject PDF text if PDF file
        image_b64 = None
        if active_file_type == "pdf":
            formatted_messages.append({
                "role": "system",
                "content": f"ATTACHED PDF CONTENT TO EVALUATE:\n{active_file_data}"
            })
        elif active_file_type == "image":
            image_b64 = active_file_data

        completion = call_groq_engine(
            client,
            messages=formatted_messages,
            is_pro=st.session_state.is_pro,
            image_b64=image_b64
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error:** {str(e)}"

def start_new_chat():
    new_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id
    st.session_state.attached_file_data = None
    st.session_state.attached_file_name = None
    st.session_state.attached_file_type = None

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
        ["🌟 Versatile Assistant", "🔥 Savage Roaster", "🧠 Career Expert"]
    )

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roaster":
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
        <p class='brand-subtitle'>Chat casually, ask questions, generate code, or attach PDF/Image for smart analysis.</p>
    </div>
""", unsafe_allow_html=True)

if not current_chat["messages"]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class='mode-card'>
                <h4>🌟 Versatile Assistant</h4>
                <p>Ask anything, generate code, write emails, or chat casually with smart AI.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='mode-card'>
                <h4>🔥 Savage Roaster</h4>
                <p>Upload a resume or text for sharp, witty roasts + actionable solutions.</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class='mode-card'>
                <h4>🧠 Career Expert</h4>
                <p>Get ATS breakdowns, interview prep, and professional career advice.</p>
            </div>
        """, unsafe_allow_html=True)

# Render Chat History
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Attached File Badge directly above Chat Bar
if st.session_state.attached_file_name:
    st.info(f"📄 **Attached File Ready:** `{st.session_state.attached_file_name}` (Send your prompt to analyze)")

# 📎 CLEAN FILE ATTACHMENT BAR (Directly above Chat Input)
with st.expander("📎 Attach PDF or Image File (Optional)", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload PDF Resume, Code Screenshot, or Image",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        key="main_attachment_input"
    )
    if uploaded_file:
        f_type, f_data = process_uploaded_file(uploaded_file)
        if f_type != "error":
            st.session_state.attached_file_type = f_type
            st.session_state.attached_file_data = f_data
            st.session_state.attached_file_name = uploaded_file.name
            st.success(f"✅ Loaded: {uploaded_file.name}")
            st.rerun()

# 💬 FULL-WIDTH CLEAN CHAT INPUT BAR (ChatGPT/Gemini Style)
prompt_text = st.chat_input(f"Type a message... ({active_mode})")

if prompt_text or st.session_state.attached_file_data:
    user_text = prompt_text if prompt_text else "Please evaluate my attached document/file."
    
    current_f_type = st.session_state.attached_file_type
    current_f_data = st.session_state.attached_file_data
    user_display_msg = user_text

    if st.session_state.attached_file_name and current_f_data:
        user_display_msg = f"📎 **[Attached File: {st.session_state.attached_file_name}]**\n\n{user_text}"
        st.session_state.attached_file_data = None
        st.session_state.attached_file_name = None
        st.session_state.attached_file_type = None

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
                active_file_type=current_f_type,
                active_file_data=current_f_data
            )
            st.markdown(response)
            current_chat["messages"].append({"role": "assistant", "content": response})

import os
import datetime
import requests
import base64
import io
import streamlit as st
from pypdf import PdfReader
from PIL import Image
from groq import Groq

PAGE_TITLE = "Advanced AI Companion"
PAGE_ICON = "🤖"
LAYOUT = "wide"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #0D1117 !important;
        color: #C9D1D9 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #161B22 !important;
        border-right: 1px solid #30363D !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 6rem !important;
        max-width: 860px !important;
        margin: 0 auto;
    }
    .brand-header { text-align: center; margin-bottom: 1.8rem; }
    .brand-title {
        font-size: clamp(1.8rem, 4vw, 2.4rem) !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        letter-spacing: -0.5px;
    }
    .brand-subtitle {
        color: #8B949E !important;
        font-size: 0.92rem !important;
        margin-top: 5px;
    }

    /* MODE CARDS */
    .mode-card {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px;
        padding: 18px;
        min-height: 140px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        transition: border-color 0.2s ease, transform 0.15s ease;
        cursor: default;
    }
    .mode-card:hover {
        border-color: #58A6FF !important;
        transform: translateY(-2px);
    }
    .mode-card h4 {
        color: #FFFFFF !important;
        font-size: 0.97rem !important;
        font-weight: 700;
        margin: 0 0 7px 0;
    }
    .mode-card p {
        color: #8B949E !important;
        font-size: 0.84rem !important;
        margin: 0;
        line-height: 1.45;
    }

    /* CHAT INPUT — SINGLE CLEAN PILL BORDER */
    div[data-testid="stChatInput"] {
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 28px !important;
        outline: none !important;
        box-shadow: none !important;
        padding: 2px 12px !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border: 1px solid #58A6FF !important;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.2) !important;
    }
    div[data-testid="stChatInput"] * { outline: none !important; }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* SIDEBAR BUTTONS */
    [data-testid="stSidebar"] button {
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    initial_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[initial_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = initial_id

# ==========================================
# FILE PROCESSOR
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
            return ("pdf", text.strip() if text.strip() else "PDF loaded, lekin text extract nahi ho saka.")
        except Exception as e:
            return ("error", f"PDF Extraction Error: {str(e)}")

    elif any(ext in file_type or file_name.lower().endswith(ext)
             for ext in ["png", "jpg", "jpeg", "webp"]):
        try:
            image = Image.open(uploaded_file)
            buffered = io.BytesIO()
            fmt = "PNG" if file_name.lower().endswith(".png") else "JPEG"
            image.save(buffered, format=fmt)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return ("image", img_b64)
        except Exception as e:
            return ("error", f"Image Error: {str(e)}")

    return ("error", "Sirf PDF ya Image (PNG, JPG, JPEG, WEBP) upload karein.")

def get_effective_api_key():
    try:
        if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")

def verify_lemonsqueezy_license(license_key):
    url = "https://api.lemonsqueezy.com/v1/licenses/validate"
    try:
        response = requests.post(url, data={"license_key": license_key.strip()}, timeout=10)
        data = response.json()
        if data.get("valid", False):
            return True, "License verified!"
        return False, data.get("error", "Invalid license key.")
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==========================================
# TONE DETECTOR
# ==========================================
def detect_user_tone(msg: str) -> str:
    """
    Returns one of:
      flirty | frustrated | angry | sad | curious | formal | greeting | casual
    """
    m = msg.lower().strip()

    flirty_words = ["honey", "sweetheart", "baby", "cutie", "gorgeous", "darling",
                    "handsome", "beautiful", "meri jaan", "jaan", "pyare", "pyari"]
    frustrated_words = ["pagal", "bakwaas", "chup", "ugh", "argh", "kuch nahi ho raha",
                        "nahi ho raha", "samajh nahi", "kya kar raha", "bekar", "faltu",
                        "thak gaya", "thak gayi", "problem hai", "masla hai", "frustrated",
                        "irritated", "pata nahi kya", "kuch nahi"]
    angry_words = ["gussa", "bura", "worst", "hate", "stupid", "idiot", "nonsense",
                   "ghanta", "bekaar", "ullu", "paagal", "ganda"]
    sad_words = ["udaas", "rona", "rota", "roti", "sad", "depressed", "dukh",
                 "takleef", "dard", "akela", "lonely", "mushkil waqt", "bura lag raha"]
    greet_words = ["hi", "hello", "hey", "hy", "hlo", "hellow", "helloo",
                   "salam", "assalam", "good morning", "good evening", "good night",
                   "kaise ho", "kya haal", "theek ho"]
    curious_words = ["kya", "kyun", "kaisa", "kaise", "kab", "kahan", "kon", "what",
                     "why", "how", "when", "where", "who", "explain", "bata", "samjhao",
                     "opinion", "sochte ho", "kya lagta"]

    words = m.split()

    # Flirty check first (overrides greeting if flirty words used)
    if any(fw in m for fw in flirty_words):
        return "flirty"
    if any(w in m for w in angry_words):
        return "angry"
    if any(w in m for w in frustrated_words):
        return "frustrated"
    if any(w in m for w in sad_words):
        return "sad"
    if any(w in m for w in greet_words) and len(words) <= 5:
        return "greeting"
    if any(w in m for w in curious_words):
        return "curious"
    if any(w in m for w in ["sir", "please", "kindly", "request", "formally"]):
        return "formal"
    return "casual"

# ==========================================
# LANGUAGE INSTRUCTION BUILDER
# ==========================================
def build_language_instruction(language: str) -> str:
    if language == "Roman Urdu":
        return """
=== LANGUAGE: 100% AUTHENTIC PAKISTANI ROMAN URDU (LATIN SCRIPT) ===

YOU ARE WRITING IN ROMAN URDU. THIS MEANS:
- Every single word must be natural Pakistani Roman Urdu
- Written in Latin (English) alphabet — NOT Urdu script
- Tone: casual, warm, like texting a Pakistani friend on WhatsApp

APPROVED ROMAN URDU VOCABULARY:
  masla        = problem/issue
  hal          = solution
  koshish      = try/effort
  woh          = he/she/they
  log          = people
  hukumat      = government
  mulk         = country
  baat         = talk/matter
  mushkil      = difficulty
  mil kar      = together
  umeedein     = hopes
  zaroorat     = need
  khayal       = thought/opinion
  waqt         = time
  zyada        = more
  thoda        = a little
  pakka        = sure/confirmed
  kamyab       = successful
  mehnat       = hard work
  jawab        = answer
  sawal        = question
  shukriya     = thank you
  banda        = person/guy
  insaan       = human
  khoon        = blood
  larai        = conflict/fight
  sulah        = peace/settlement
  guftagoo     = dialogue/conversation
  muqami       = local
  bara         = big/large
  poori        = all/entire
  kaam         = work/task
  khas         = special
  laayak       = worthy/capable
  lagta hai    = it seems / I feel
  mila         = received/got
  amaan        = safety/peace
  sukoon       = peace of mind
  raasta       = path/option
  hosla        = courage/morale
  dil          = heart
  yaar/bhai    = friend/buddy
  achha        = good/okay
  theek        = fine/correct

STRICTLY BANNED HINDI WORDS — NEVER WRITE THESE:
  samasya      → masla
  vikalp       → option / raasta
  ekjut        → mil kar / ikatha
  hove         → ho / hoga
  samadhan     → hal
  sthaniya     → muqami / local
  bhaavishyavani → andaza
  surajit      → theek / behtar
  adhik        → zyada
  na-kammi     → kami
  jatil        → mushkil
  ashaon       → umeedein
  manna        → khayal / sochna
  ve           → woh
  vishesh      → khas
  adarsh       → achi misaal
  mehsus       → lagta hai
  avashyak     → zaroori
  saari        → poori
  karya        → kaam
  badaa        → bara
  prayaas      → koshish
  prapt        → mila
  nishchit     → pakka
  yogya        → laayak
  uttar        → jawab
  prashn       → sawal
  dhanyavaad   → shukriya
  vyakti       → banda / insaan
  parishram    → mehnat
  safal        → kamyab
  shanti       → amaan / sukoon
  ekta         → ittehad
  dono deshon  → dono mulkon
  sunne ke liye taiyar → sunne ko taiyar

GRAMMAR:
  - Masculine/neutral address: kar rahe ho, puch rahe ho, aaye ho, soch rahe ho
  - Short, natural sentences — no lecture paragraphs
  - Mix short punchy lines with slightly longer explanations
"""
    elif language == "Roman Hindi":
        return "Respond in natural conversational Roman Hindi using Latin script. Use everyday Hindustani vocabulary. Be warm and natural. Do not mix Urdu-specific words."
    elif language == "Urdu (اردو)":
        return "صرف اردو رسم الخط میں جواب دیں۔ فصیح اور قدرتی اردو استعمال کریں۔ ہندی الفاظ سے مکمل گریز کریں۔"
    elif language == "Hindi (हिंदी)":
        return "केवल हिंदी देवनागरी लिपि में जवाब दें। स्वाभाविक और सरल हिंदी उपयोग करें।"
    else:
        return f"STRICT: Respond entirely in {language}. Do not mix any other language."

# ==========================================
# TONE PERSONA BUILDER
# ==========================================
def build_tone_persona(tone: str, last_user_msg: str) -> str:
    if tone == "flirty":
        return f"""
USER TONE DETECTED: FLIRTY / PLAYFUL
The user's message has a warm, playful, or slightly flirtatious energy (e.g., they called you "honey", "jaan", etc.).

YOUR RESPONSE STYLE:
1. Be charming, warm, and lightly playful — professional but with a smile.
2. Respond to the flirty energy naturally — don't ignore it, don't overdo it.
3. Show genuine interest in them: ask what brought them here, what's on their mind.
4. Keep it classy — fun and engaging but never inappropriate.
5. Use a warm, slightly teasing tone: "Acha ji, toh aaj kya kaam aa saktay hain hum?"
"""
    elif tone == "frustrated":
        return f"""
USER TONE DETECTED: FRUSTRATED / STRESSED
The user seems frustrated, stuck, or overwhelmed.

YOUR RESPONSE STYLE:
1. FIRST: Acknowledge their frustration with genuine empathy — don't jump to solutions immediately.
2. Show that you understand how annoying/hard this feels.
3. Give them hosla (encouragement): remind them this is fixable, they're not alone.
4. Then calmly offer to help — ask what exactly is going wrong.
5. Warm, patient, supportive tone — like a calm friend who has your back.
"""
    elif tone == "angry":
        return f"""
USER TONE DETECTED: ANGRY / VENTING
The user is venting or expressing strong anger/frustration.

YOUR RESPONSE STYLE:
1. DO NOT argue back or get defensive.
2. Let them vent — validate their feelings first.
3. Use a calm, understanding tone: "Yaar, sun — main samajhta hoon, yeh sach mein bura situation hai."
4. After validation, gently steer toward what can be done / how you can help.
5. Never be dismissive. Never lecture them about being angry.
"""
    elif tone == "sad":
        return f"""
USER TONE DETECTED: SAD / LOW
The user seems sad, down, or going through a hard time.

YOUR RESPONSE STYLE:
1. Lead with deep empathy and warmth — make them feel heard and not alone.
2. Do NOT rush to advice or solutions — sit with them emotionally first.
3. Use comforting language: "Yaar, yeh sun ke dil bhaari ho gaya — kya chal raha hai?"
4. Show genuine concern and ask them to share more if they want.
5. Offer to help in whatever way they need — whether it's just listening or solving a problem.
"""
    elif tone == "greeting":
        return f"""
USER TONE DETECTED: SIMPLE GREETING
The user said a casual hello/greeting.

YOUR RESPONSE STYLE:
1. Reply with ONE warm, natural, unique greeting — do NOT repeat multiple greeting words.
2. Show personality and warmth — not a robotic "How can I assist you today?"
3. Ask what's on their mind today in a natural, engaging way.
4. Keep it SHORT — 2 to 3 sentences maximum.
5. NEVER use more than one greeting word (e.g., don't say "Hey! Hello! Hi there!").
"""
    elif tone == "curious":
        return f"""
USER TONE DETECTED: CURIOUS / INQUISITIVE
The user is asking something they genuinely want to understand.

YOUR RESPONSE STYLE:
1. Match their curiosity — be genuinely engaged and enthusiastic.
2. Give a clear, well-researched, multi-angle answer.
3. Use simple relatable language — avoid jargon unless they ask for it.
4. Where relevant, share your own perspective or opinion.
5. End with an invitation to dig deeper if they want.
"""
    elif tone == "formal":
        return f"""
USER TONE DETECTED: FORMAL / PROFESSIONAL
The user is writing in a formal or professional manner.

YOUR RESPONSE STYLE:
1. Match their professional tone — structured, clear, respectful.
2. Use proper language appropriate to the context.
3. Be thorough and accurate without being overly verbose.
4. Offer next steps or follow-up options at the end.
"""
    else:  # casual
        return f"""
USER TONE DETECTED: CASUAL / RELAXED
The user is just having a normal, relaxed conversation.

YOUR RESPONSE STYLE:
1. Be natural, friendly, and conversational — like talking to a smart friend.
2. Don't be overly formal or robotic.
3. Match their energy — if they're being chill, be chill.
4. Give solid, helpful responses without unnecessary fluff.
"""

# ==========================================
# GROQ ENGINE
# ==========================================
def call_groq_engine(client, messages, is_pro=False, image_b64=None):
    primary_model = "llama-3.3-70b-versatile" if is_pro else "llama-3.1-8b-instant"
    fallback_model = "llama-3.1-8b-instant"
    vision_model = "llama-3.2-11b-vision-instruct"

    if image_b64:
        try:
            text_prompt = "\n".join([
                m.get("content", "") for m in messages
                if isinstance(m.get("content"), str)
            ])
            vision_messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }]
            return client.chat.completions.create(
                model=vision_model,
                messages=vision_messages,
                max_tokens=1200,
                temperature=0.75
            )
        except Exception:
            pass

    kwargs = {
        "messages": messages,
        "temperature": 0.75,
        "max_tokens": 1200,
        "frequency_penalty": 0.25,
        "presence_penalty": 0.45,
    }
    try:
        return client.chat.completions.create(model=primary_model, **kwargs)
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "rate_limit" in err or "tokens" in err:
            return client.chat.completions.create(model=fallback_model, **kwargs)
        raise e

def generate_chat_title(first_user_msg: str) -> str:
    effective_key = get_effective_api_key()
    if not effective_key:
        return "New Chat"
    try:
        client = Groq(api_key=effective_key)
        prompt = f"Summarize into a short 2-4 word chat title: '{first_user_msg[:150]}'"
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

# ==========================================
# AI RESPONSE ENGINE
# ==========================================
def get_ai_response(messages_history, active_mode, roast_level, language,
                    active_file_type=None, active_file_data=None):
    effective_key = get_effective_api_key()
    if not effective_key:
        return "⚠️ **Error:** GROQ_API_KEY missing hai! Please `.streamlit/secrets.toml` check karein."

    try:
        client = Groq(api_key=effective_key)

        # Get last user message
        last_user_msg = ""
        for m in reversed(messages_history):
            if m["role"] == "user":
                last_user_msg = m["content"].strip()
                break

        last_lower = last_user_msg.lower()

        # Detect tone
        user_tone = detect_user_tone(last_lower)

        # Build tone persona
        tone_persona = build_tone_persona(user_tone, last_lower)

        # Language instruction
        lang_instruction = build_language_instruction(language)

        # Bot capability check
        is_asking_about_bot = any(w in last_lower for w in [
            "tum kon ho", "tumhare kya feature", "tum kya kar sakte ho",
            "features", "who are you", "what can you do", "kya kar sakte",
            "kya ho tum", "batao apne baare"
        ])

        # ─── MODE: Versatile Assistant ───
        if active_mode == "🌟 Versatile Assistant":
            if is_asking_about_bot:
                mode_persona = """
YOU ARE AN ADVANCED MULTI-MODAL AI COMPANION.
Explain your capabilities warmly and clearly:
1. 💬 General Q&A, Discussions & Brainstorming
2. 💻 Coding, Debugging & Architecture
3. 📄 PDF & Image Analysis (Multimodal Vision)
4. 🔥 Savage Roasting Mode
5. 🧠 Career Guidance & ATS Optimization
6. 🌍 Political, Social & Research Analysis
"""
            else:
                mode_persona = """
YOU ARE AN ADVANCED, EMOTIONALLY INTELLIGENT AI ASSISTANT.
- Give well-researched, nuanced, multi-angle responses.
- For sensitive topics: show empathy FIRST, then give analysis.
- Political/social topics: be balanced but have your own clear, reasoned opinion.
- Share genuine perspective — don't just list neutral bullet points like Wikipedia.
- Every response must feel human, warm, and thoughtful.
"""

        # ─── MODE: Career Expert ───
        elif active_mode == "🧠 Career Expert":
            mode_persona = """
YOU ARE A PROFESSIONAL CAREER & ATS RESUME EXPERT.
- Give structured, specific, research-backed career advice.
- Cover ATS scoring, keyword optimization, interview prep, industry guidance.
- Be direct and practical — no generic advice.
- Show genuine interest in the user's career growth.
"""

        # ─── MODE: Savage Roaster ───
        else:
            intensity_map = {
                "Normal": "Funny, sarcastic, lighthearted.",
                "Medium": "Sharp, brutally honest, witty.",
                "Hard": "ULTIMATE SAVAGE — ruthlessly funny like a top stand-up comedian."
            }

            if user_tone == "greeting" and not active_file_data:
                mode_persona = """
YOU ARE A WITTY, HIGH-ENERGY DESI ROASTER.
User said a casual greeting. No file attached.
- Reply with ONE fun sarcastic greeting (no repeated greetings).
- Ask what they want roasted in a funny, punchy way.
- DO NOT write 'The Roast' or 'How to Fix It' sections.
"""
            elif active_file_data:
                mode_persona = f"""
YOU ARE AN AI ROASTER & CAREER CONSULTANT.
Roast Level: {roast_level} — {intensity_map.get(roast_level)}
A FILE IS ATTACHED. Structure:
1. 🔥 **The Roast:** Witty, specific attack on actual weak points.
2. 💡 **How to Fix It:** 2-3 clear, actionable improvement steps.
"""
            else:
                mode_persona = f"""
YOU ARE A SAVAGE DESI ROASTER.
Roast Level: {roast_level} — {intensity_map.get(roast_level)}
Target: '{last_user_msg}'
- Real savage roast — hilarious, punchy, original.
- NO fake scripted dialogues (Trump: ... Tum: ...) — cringe hai.
- NO 'How to Fix It' unless resume/code is actually given.
- Find genuinely funny, specific angles. No generic insults.
"""

        # Assemble final system prompt
        system_prompt = f"""
{mode_persona}

=== TONE ADAPTATION ===
{tone_persona}

=== LANGUAGE ===
{lang_instruction}

=== ANTI-REPETITION LAW — MANDATORY ===
- EVERY sentence must add NEW information, angle, or perspective.
- NEVER rephrase the same point in different words.
- NEVER start with the same word you just used in the previous sentence.
- For GREETINGS: use only ONE greeting word maximum — never stack "Hey! Hello! Hi there!".
- Vary sentence length: mix short punchy lines with slightly longer explanations.

=== NEUTRALITY ===
- Do NOT open with religious greetings (Assalam, Namaste, etc.).
- Be respectful and thoughtful on sensitive topics.
"""

        formatted_messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 6 exchanges)
        for msg in messages_history[-6:]:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        # Inject file content
        image_b64 = None
        if active_file_type == "pdf":
            formatted_messages.append({
                "role": "system",
                "content": f"ATTACHED PDF CONTENT:\n{active_file_data}"
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
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;
                    border-bottom:1px solid #30363D; padding-bottom:12px;">
            <span style="font-size:1.6rem;">🤖</span>
            <h3 style="margin:0; color:#FFFFFF; font-size:1.05rem; font-weight:700;">AI Companion</h3>
        </div>
    """, unsafe_allow_html=True)

    # Status Badge
    if st.session_state.is_pro:
        st.markdown("🔥 **Status:** <span style='background:#238636; color:#FFF; padding:2px 10px; border-radius:10px; font-size:0.73rem; font-weight:600;'>Pro Active</span>", unsafe_allow_html=True)
    else:
        st.markdown("🟢 **Status:** <span style='background:#1F6FEB; color:#FFF; padding:2px 10px; border-radius:10px; font-size:0.73rem; font-weight:600;'>Free Plan</span>", unsafe_allow_html=True)

        st.markdown("""
            <div style="background:#0D1117; border:1px solid #30363D; border-radius:9px; padding:11px; margin:10px 0;">
                <p style="margin:0 0 7px 0; font-size:0.79rem; color:#8B949E;">Faster models & priority access.</p>
                <a href="https://airoaster.lemonsqueezy.com/checkout/buy/ec7ff9c8-e11c-4102-aa52-3f5884f8fb2c"
                   target="_blank" style="text-decoration:none;">
                    <button style="width:100%; background:#238636; color:#FFF; border:none; padding:7px;
                                   border-radius:7px; cursor:pointer; font-weight:700; font-size:0.84rem;">
                        ⚡ Upgrade to Pro ($6)
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🔑 Activate License"):
            license_input = st.text_input("License Key:", type="password", key="license_key_input")
            if st.button("✅ Activate Pro", use_container_width=True):
                if license_input:
                    valid, msg = verify_lemonsqueezy_license(license_input)
                    if valid:
                        st.session_state.is_pro = True
                        st.success("Pro Activated!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter your license key.")

    # Developer Access
    with st.expander("🛠️ Developer Access"):
        if st.session_state.is_pro:
            st.info("⚡ **Dev Pro Mode** is active.")
            if st.button("🔴 Deactivate", use_container_width=True):
                st.session_state.is_pro = False
                st.success("Switched to Free Mode!")
                st.rerun()
        else:
            entered_key = st.text_input("Secret Key:", type="password", key="dev_key_input")
            if st.button("🔓 Activate Dev Pro", use_container_width=True):
                dev_secret = None
                try:
                    if "DEV_SECRET_KEY" in st.secrets and st.secrets["DEV_SECRET_KEY"]:
                        dev_secret = st.secrets["DEV_SECRET_KEY"]
                except Exception:
                    pass
                if not dev_secret:
                    st.error("❌ DEV_SECRET_KEY not configured in secrets!")
                elif entered_key == dev_secret:
                    st.session_state.is_pro = True
                    st.success("🎉 Dev Pro Activated!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Secret Key!")

    st.markdown("---")

    language = st.selectbox(
        "🌐 Language:",
        ["Roman Urdu", "Roman Hindi", "English", "Urdu (اردو)",
         "Hindi (हिंदी)", "Spanish", "French", "German", "Arabic", "Turkish"]
    )

    active_mode = st.radio(
        "🎯 AI Mode:",
        ["🌟 Versatile Assistant", "🔥 Savage Roaster", "🧠 Career Expert"]
    )

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roaster":
        roast_level = st.select_slider(
            "🔥 Roast Intensity:",
            options=["Normal", "Medium", "Hard"],
            value="Medium"
        )

    st.markdown("---")
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("<p style='margin:10px 0 5px 0; color:#8B949E; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>Recent Chats</p>", unsafe_allow_html=True)
    for c_id in list(st.session_state.all_chats.keys())[::-1]:
        chat_info = st.session_state.all_chats[c_id]
        col_btn, col_del = st.columns([4.2, 0.8])
        prefix = "💬 " if c_id == st.session_state.current_chat_id else ""
        if col_btn.button(f"{prefix}{chat_info['title']}", key=f"btn_{c_id}", use_container_width=True):
            st.session_state.current_chat_id = c_id
            st.rerun()
        if col_del.button("🗑️", key=f"del_{c_id}"):
            delete_chat(c_id)
            st.rerun()

# ==========================================
# MAIN INTERFACE
# ==========================================
st.markdown("""
    <div class='brand-header'>
        <h1 class='brand-title'>Advanced AI Companion</h1>
        <p class='brand-subtitle'>Chat casually, ask anything, generate code, or attach PDF/Image for smart analysis.</p>
    </div>
""", unsafe_allow_html=True)

# Welcome cards (only when no messages)
if not current_chat["messages"]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class='mode-card'>
                <h4>🌟 Versatile Assistant</h4>
                <p>Ask anything, code, write, brainstorm, or just have a smart conversation.</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='mode-card'>
                <h4>🔥 Savage Roaster</h4>
                <p>Upload your resume or topic for sharp, witty roasts + real solutions.</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class='mode-card'>
                <h4>🧠 Career Expert</h4>
                <p>ATS scoring, interview prep, and professional career strategy advice.</p>
            </div>
        """, unsafe_allow_html=True)

# Render chat history
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# CHAT INPUT — SINGLE PILL WITH ATTACHMENT
# ==========================================
chat_input_data = st.chat_input(
    f"Type a message... ({active_mode})",
    accept_file=True,
    file_type=["pdf", "png", "jpg", "jpeg", "webp"]
)

if chat_input_data:
    prompt_text = chat_input_data.get("text", "")
    uploaded_files = chat_input_data.get("files", [])

    current_f_type = None
    current_f_data = None
    user_display_msg = prompt_text

    if uploaded_files:
        attached_file = uploaded_files[0]
        f_type, f_data = process_uploaded_file(attached_file)
        if f_type != "error":
            current_f_type = f_type
            current_f_data = f_data
            file_name = attached_file.name
            user_display_msg = (
                f"📎 **[Attached: {file_name}]**\n\n{prompt_text}"
                if prompt_text else
                f"📎 **[Attached: {file_name}]**\nPlease evaluate my attached file."
            )
        else:
            st.error(f_data)

    if user_display_msg or current_f_type:
        # Auto-generate title on first message
        sample_text = prompt_text if prompt_text else "Conversation"
        if not current_chat["messages"] or current_chat["title"] == "New Chat":
            current_chat["title"] = generate_chat_title(sample_text)

        # Show user message
        st.chat_message("user").markdown(user_display_msg)
        current_chat["messages"].append({"role": "user", "content": user_display_msg})

        # Generate and show AI response
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

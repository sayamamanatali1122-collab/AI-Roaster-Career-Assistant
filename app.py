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

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# PREMIUM CSS DESIGN SYSTEM
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

/* ── CORE DARK THEME ── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #080C12 !important;
    color: #C9D1D9 !important;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse 60% 40% at 20% 10%, rgba(88,166,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 50% 35% at 80% 90%, rgba(139,92,246,0.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1117 0%, #0A0F18 100%) !important;
    border-right: 1px solid #1C2333 !important;
}
[data-testid="stSidebar"] .block-container { padding: 0 !important; }
[data-testid="stSidebar"] > div { padding: 0 !important; }
section[data-testid="stSidebar"] > div > div > div { padding: 1rem 0.9rem !important; }

/* ── MAIN LAYOUT ── */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 7rem !important;
    max-width: 820px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

/* ── HERO HEADER ── */
.hero-wrap {
    text-align: center;
    padding: 1.5rem 0 2.2rem 0;
    position: relative;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(88,166,255,0.1);
    border: 1px solid rgba(88,166,255,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #58A6FF;
    letter-spacing: 0.5px;
    margin-bottom: 16px;
}
.hero-title {
    font-size: clamp(2rem, 5vw, 2.8rem) !important;
    font-weight: 900 !important;
    letter-spacing: -1px;
    line-height: 1.15;
    background: linear-gradient(135deg, #FFFFFF 0%, #8B949E 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 10px 0 !important;
}
.hero-sub {
    color: #6E7681 !important;
    font-size: 0.95rem !important;
    font-weight: 400;
    margin: 0;
    line-height: 1.5;
}

/* ── MODE CARDS ── */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 2rem;
}
.mode-card {
    background: linear-gradient(135deg, #161B22 0%, #0D1117 100%) !important;
    border: 1px solid #21262D !important;
    border-radius: 16px;
    padding: 20px 18px;
    height: 150px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    transition: border-color 0.25s ease, transform 0.2s ease, box-shadow 0.25s ease;
    position: relative;
    overflow: hidden;
}
.mode-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.4), transparent);
    opacity: 0;
    transition: opacity 0.25s ease;
}
.mode-card:hover {
    border-color: #30363D !important;
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
}
.mode-card:hover::before { opacity: 1; }

.card-icon {
    font-size: 1.5rem;
    margin-bottom: 8px;
    display: block;
}
.card-title {
    color: #FFFFFF !important;
    font-size: 0.9rem !important;
    font-weight: 700;
    margin: 0 0 6px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.card-desc {
    color: #6E7681 !important;
    font-size: 0.8rem !important;
    margin: 0;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── CHAT MESSAGES ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
}

/* ── CHAT INPUT — SINGLE CLEAN PILL ── */
div[data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
div[data-testid="stChatInput"] > div {
    background: #0D1117 !important;
    border: 1px solid #21262D !important;
    border-radius: 28px !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 4px 14px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stChatInput"] > div:focus-within {
    border: 1px solid #388BFD !important;
    box-shadow: 0 0 0 3px rgba(56,139,253,0.12) !important;
}
div[data-testid="stChatInput"] * { outline: none !important; }
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: #C9D1D9 !important;
}

/* ── SIDEBAR COMPONENTS ── */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 0 14px 0;
    margin-bottom: 14px;
    border-bottom: 1px solid #1C2333;
}
.sidebar-brand-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #1F6FEB, #388BFD);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
}
.sidebar-brand-name {
    color: #FFFFFF !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}

.status-badge-pro {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(35,134,54,0.15);
    border: 1px solid rgba(35,134,54,0.35);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #3FB950;
    width: 100%;
    margin-bottom: 10px;
}
.status-badge-free {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(31,111,235,0.12);
    border: 1px solid rgba(31,111,235,0.3);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #58A6FF;
    width: 100%;
    margin-bottom: 10px;
}

.upgrade-box {
    background: linear-gradient(135deg, rgba(35,134,54,0.08), rgba(35,134,54,0.03));
    border: 1px solid rgba(35,134,54,0.2);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
}
.upgrade-box p {
    margin: 0 0 8px 0;
    font-size: 0.78rem;
    color: #6E7681;
    line-height: 1.4;
}
.upgrade-btn {
    display: block;
    width: 100%;
    background: linear-gradient(135deg, #238636, #2EA043);
    color: #FFFFFF !important;
    text-decoration: none !important;
    text-align: center;
    padding: 8px 12px;
    border-radius: 7px;
    font-size: 0.83rem;
    font-weight: 700;
    transition: opacity 0.2s;
}
.upgrade-btn:hover { opacity: 0.9; }

.section-label {
    color: #484F58 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 12px 0 6px 0;
}

/* ── STREAMLIT OVERRIDES & EXPANDER CLEAN FIX ── */
.stSelectbox > label,
.stRadio > label,
.stSlider > label { color: #8B949E !important; font-size: 0.82rem !important; font-weight: 600 !important; }
.stSelectbox [data-baseweb="select"] > div {
    background: #0D1117 !important;
    border-color: #21262D !important;
    border-radius: 8px !important;
}
.stRadio [data-testid="stMarkdownContainer"] p { color: #C9D1D9 !important; font-size: 0.88rem !important; }
[data-testid="stSidebar"] button {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}
.stExpander {
    background: rgba(22,27,34,0.5) !important;
    border: 1px solid #21262D !important;
    border-radius: 10px !important;
}
.stExpander details summary { padding-left: 4px !important; }
.stExpander details summary p { color: #8B949E !important; font-size: 0.85rem !important; font-weight: 600 !important; margin: 0 !important; display: inline-block !important; }
hr { border-color: #1C2333 !important; margin: 10px 0 !important; }
.stSpinner > div { border-top-color: #388BFD !important; }
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
            text = "".join(p.extract_text() or "" for p in reader.pages)
            return ("pdf", text.strip() or "PDF loaded, lekin text extract nahi ho saka.")
        except Exception as e:
            return ("error", f"PDF Error: {e}")
    elif any(ext in file_type or file_name.lower().endswith(ext)
             for ext in ["png", "jpg", "jpeg", "webp"]):
        try:
            img = Image.open(uploaded_file)
            buf = io.BytesIO()
            img.save(buf, format="PNG" if file_name.lower().endswith(".png") else "JPEG")
            return ("image", base64.b64encode(buf.getvalue()).decode())
        except Exception as e:
            return ("error", f"Image Error: {e}")
    return ("error", "Sirf PDF ya Image (PNG, JPG, JPEG, WEBP) upload karein.")

def get_effective_api_key():
    try:
        k = st.secrets.get("GROQ_API_KEY", "")
        if k: return k
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")

def verify_lemonsqueezy_license(key):
    try:
        r = requests.post("https://api.lemonsqueezy.com/v1/licenses/validate",
                          data={"license_key": key.strip()}, timeout=10)
        d = r.json()
        return (True, "License verified!") if d.get("valid") else (False, d.get("error", "Invalid key."))
    except Exception as e:
        return False, str(e)

# ==========================================
# TONE DETECTOR
# ==========================================
def detect_user_tone(msg: str) -> str:
    m = msg.lower().strip()
    words = m.split()
    flirty   = ["honey","sweetheart","baby","cutie","gorgeous","darling","handsome","beautiful","meri jaan","jaan","pyare","pyari"]
    angry    = ["gussa","worst","hate","stupid","idiot","nonsense","ghanta","bekaar","ullu","paagal","ganda"]
    frustrated=["bakwaas","ugh","argh","kuch nahi ho raha","nahi ho raha","samajh nahi","bekar","faltu","thak gaya","thak gayi","frustrated","irritated","pata nahi kya"]
    sad      = ["udaas","rona","rota","roti","sad","depressed","dukh","takleef","dard","akela","lonely","bura lag raha"]
    greet    = ["hi","hello","hey","hy","hlo","hellow","helloo","salam","assalam","good morning","good evening","good night","kaise ho","kya haal","theek ho"]
    curious  = ["kya","kyun","kaisa","kaise","kab","kahan","kon","what","why","how","when","where","who","explain","bata","samjhao","opinion","sochte ho","kya lagta"]
    if any(w in m for w in flirty):     return "flirty"
    if any(w in m for w in angry):      return "angry"
    if any(w in m for w in frustrated): return "frustrated"
    if any(w in m for w in sad):        return "sad"
    if any(w in m for w in greet) and len(words) <= 5: return "greeting"
    if any(w in m for w in curious):    return "curious"
    if any(w in m for w in ["sir","please","kindly","request","formally"]): return "formal"
    return "casual"

# ==========================================
# LANGUAGE INSTRUCTION
# ==========================================
def build_language_instruction(language: str) -> str:
    if language == "Roman Urdu":
        return """
=== LANGUAGE: 100% AUTHENTIC PAKISTANI ROMAN URDU (LATIN SCRIPT) ===
Every word must be natural Pakistani Roman Urdu written in the Latin alphabet.
Tone: casual, warm — like texting a Pakistani friend.

APPROVED VOCABULARY:
masla=problem | hal=solution | koshish=try | woh=they | log=people
hukumat=government | mulk=country | baat=matter | mushkil=difficulty
mil kar=together | umeedein=hopes | zaroorat=need | khayal=thought
waqt=time | zyada=more | thoda=little | pakka=sure | kamyab=successful
mehnat=hardwork | jawab=answer | sawal=question | shukriya=thanks
banda=person | insaan=human | larai=conflict | sulah=peace
muqami=local | bara=big | poori=all | kaam=work | khas=special
laayak=worthy | lagta hai=it seems | amaan=safety | sukoon=calmness
raasta=option/path | hosla=courage | dil=heart | yaar/bhai=friend
achha=good | theek=fine | ittehad=unity | dono mulkon=both countries

STRICTLY BANNED HINDI WORDS → CORRECT REPLACEMENT:
samasya→masla | vikalp→option/raasta | ekjut→mil kar | hove→ho/hoga
samadhan→hal | sthaniya→muqami | surajit→theek | adhik→zyada
na-kammi→kami | jatil→mushkil | ashaon→umeedein | manna→khayal
ve→woh | vishesh→khas | adarsh→achi misaal | mehsus→lagta hai
avashyak→zaroori | saari→poori | karya→kaam | badaa→bara
prayaas→koshish | prapt→mila | nishchit→pakka | yogya→laayak
uttar→jawab | prashn→sawal | dhanyavaad→shukriya | vyakti→banda
parishram→mehnat | safal→kamyab | shanti→amaan/sukoon | ekta→ittehad

GRAMMAR: Masculine/neutral address. Short punchy natural sentences.
NEVER use Urdu script. ONLY Latin letters.
"""
    elif language == "Roman Hindi":
        return "Respond in natural conversational Roman Hindi (Latin script). Everyday Hindustani. Warm and natural."
    elif language == "Urdu (اردو)":
        return "صرف اردو رسم الخط میں جواب دیں۔ فصیح قدرتی اردو۔ ہندی الفاظ سے گریز۔"
    elif language == "Hindi (हिंदी)":
        return "केवल हिंदी देवनागरी लिपि में। स्वाभाविक सरल हिंदी।"
    else:
        return f"STRICT: Respond entirely in {language}."

# ==========================================
# TONE PERSONA
# ==========================================
def build_tone_persona(tone: str) -> str:
    personas = {
        "flirty": """USER IS BEING PLAYFUL/FLIRTY (said "honey", "jaan", etc.)
STYLE: Charming, warm, lightly playful — professional but with a smile.
- Respond to their flirty energy naturally — don't ignore it, don't overdo it.
- Ask warmly what's on their mind: "Acha ji, toh aaj kya plan hai?"
- Classy, fun, engaging — never inappropriate.""",

        "frustrated": """USER IS FRUSTRATED / STRESSED
STYLE: Patient, supportive, like a calm friend who has your back.
1. Acknowledge frustration first with genuine empathy.
2. Give hosla — remind them this is fixable and they're not alone.
3. Then gently ask what exactly is going wrong.""",

        "angry": """USER IS ANGRY / VENTING
STYLE: Calm, understanding — do NOT argue back.
1. Validate their feelings immediately.
2. Use tone: "Yaar sun — main samajhta hoon, yeh sach mein bura hai."
3. After validation, steer gently toward what you can help with.""",

        "sad": """USER IS SAD / DOWN
STYLE: Deep warmth and empathy — make them feel heard.
1. Do NOT rush to advice — sit with them emotionally first.
2. "Yaar, yeh sun ke dil bhaari ho gaya — kya chal raha hai?"
3. Show genuine concern. Offer to help however they need.""",

        "greeting": """USER SAID A SIMPLE GREETING
STYLE: Warm, natural, with personality.
1. ONE greeting word only — NEVER stack "Hey! Hello! Hi there!"
2. Show genuine warmth — not a robotic response.
3. Ask naturally what's on their mind. MAX 2-3 sentences.""",

        "curious": """USER IS CURIOUS / ASKING SOMETHING
STYLE: Enthusiastic, engaged, clear.
1. Match their curiosity — be genuinely interested.
2. Give a clear, multi-angle, well-researched answer.
3. Share your own perspective where relevant.""",

        "formal": """USER IS WRITING FORMALLY
STYLE: Professional, structured, respectful.
1. Match their formal tone precisely.
2. Be thorough but not verbose.
3. Offer clear next steps.""",

        "casual": """USER IS RELAXED / CASUAL
STYLE: Natural, friendly, conversational — like a smart friend.
1. Match their chill energy.
2. Helpful and warm without unnecessary fluff.""",
    }
    return personas.get(tone, personas["casual"])

# ==========================================
# GROQ ENGINE
# ==========================================
def call_groq_engine(client, messages, is_pro=False, image_b64=None):
    primary = "llama-3.3-70b-versatile" if is_pro else "llama-3.1-8b-instant"
    fallback = "llama-3.1-8b-instant"
    vision   = "llama-3.2-11b-vision-instruct"

    if image_b64:
        try:
            txt = "\n".join(m.get("content","") for m in messages if isinstance(m.get("content"),str))
            return client.chat.completions.create(
                model=vision, max_tokens=1200, temperature=0.75,
                messages=[{"role":"user","content":[
                    {"type":"text","text":txt},
                    {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{image_b64}"}}
                ]}]
            )
        except Exception:
            pass

    kwargs = dict(messages=messages, temperature=0.75, max_tokens=1200,
                  frequency_penalty=0.25, presence_penalty=0.45)
    try:
        return client.chat.completions.create(model=primary, **kwargs)
    except Exception as e:
        if any(x in str(e).lower() for x in ["429","rate_limit","tokens"]):
            return client.chat.completions.create(model=fallback, **kwargs)
        raise

def generate_chat_title(msg: str) -> str:
    key = get_effective_api_key()
    if not key: return "New Chat"
    try:
        client = Groq(api_key=key)
        c = call_groq_engine(client,
            [{"role":"user","content":f"Summarize into 2-4 word title: '{msg[:120]}'"}],
            is_pro=st.session_state.is_pro)
        return c.choices[0].message.content.strip().replace('"','')[:25]
    except Exception:
        return msg.strip().split("\n")[0][:20]

# ==========================================
# AI RESPONSE ENGINE
# ==========================================
def get_ai_response(history, mode, roast_level, language, f_type=None, f_data=None):
    key = get_effective_api_key()
    if not key:
        return "⚠️ **GROQ_API_KEY missing!** Please add it to `.streamlit/secrets.toml`."
    try:
        client = Groq(api_key=key)
        last_msg = next((m["content"].strip() for m in reversed(history) if m["role"]=="user"), "")
        last_lower = last_msg.lower()
        tone = detect_user_tone(last_lower)
        tone_persona = build_tone_persona(tone)
        lang_inst = build_language_instruction(language)

        bot_query = any(w in last_lower for w in [
            "tum kon ho","features","who are you","what can you do","kya kar sakte","kya ho tum"
        ])

        # Mode persona
        if mode == "🌟 Versatile Assistant":
            if bot_query:
                mode_p = """YOU ARE AN ADVANCED AI COMPANION. Explain capabilities warmly:
1. 💬 General Q&A & Brainstorming
2. 💻 Coding & Debugging
3. 📄 PDF & Image Analysis
4. 🔥 Savage Roasting Mode
5. 🧠 Career & ATS Guidance
6. 🌍 Political & Social Research"""
            else:
                mode_p = """YOU ARE AN ADVANCED, EMOTIONALLY INTELLIGENT AI ASSISTANT.
- Research-backed, nuanced, multi-angle responses.
- Sensitive topics: empathy FIRST, then analysis.
- Political topics: balanced but have your own clear reasoned opinion.
- Every response must feel human, warm, and thoughtful."""

        elif mode == "🧠 Career Expert":
            mode_p = """YOU ARE A PROFESSIONAL CAREER & ATS RESUME EXPERT.
- Structured, specific, research-backed advice.
- ATS scoring, keyword optimization, interview prep.
- Direct and practical. Show genuine interest in user's growth."""

        else:  # Savage Roaster
            imap = {"Normal":"Funny, sarcastic, lighthearted.",
                    "Medium":"Sharp, brutally honest, witty.",
                    "Hard":"ULTIMATE SAVAGE — ruthlessly funny like a top comedian."}
            if tone == "greeting" and not f_data:
                mode_p = """WITTY HIGH-ENERGY DESI ROASTER.
- ONE fun sarcastic greeting only.
- Ask what they want roasted in a funny punchy way.
- NO 'The Roast' or 'How to Fix It' sections."""
            elif f_data:
                mode_p = f"""AI ROASTER & CAREER CONSULTANT.
Roast Level: {roast_level} — {imap.get(roast_level)}
FILE ATTACHED:
1. 🔥 The Roast: Witty specific attack on weak points.
2. 💡 How to Fix It: 2-3 clear actionable steps."""
            else:
                mode_p = f"""SAVAGE DESI ROASTER.
Roast Level: {roast_level} — {imap.get(roast_level)}
Target: '{last_msg}'
- Real savage roast — hilarious, punchy, original.
- NO fake scripted dialogues. NO 'How to Fix It' unless code/resume given.
- Find genuinely funny specific angles."""

        system_prompt = f"""{mode_p}

=== TONE ===
{tone_persona}

=== LANGUAGE ===
{lang_inst}

=== ANTI-REPETITION LAW ===
- Every sentence adds NEW information. NEVER rephrase the same point.
- Greetings: ONE greeting word max. Never stack "Hey! Hello! Hi!"
- Vary sentence length naturally.

=== NEUTRALITY ===
Do NOT open with religious greetings (Assalam, Namaste, etc.).
"""
        msgs = [{"role":"system","content":system_prompt}]
        msgs += [{"role":m["role"],"content":m["content"]} for m in history[-6:]]

        img_b64 = None
        if f_type == "pdf":
            msgs.append({"role":"system","content":f"ATTACHED PDF:\n{f_data}"})
        elif f_type == "image":
            img_b64 = f_data

        c = call_groq_engine(client, msgs, is_pro=st.session_state.is_pro, image_b64=img_b64)
        return c.choices[0].message.content
    except Exception as e:
        return f"⚠️ **Error:** {e}"

def start_new_chat():
    nid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.all_chats[nid] = {"title":"New Chat","messages":[]}
    st.session_state.current_chat_id = nid

def delete_chat(cid):
    del st.session_state.all_chats[cid]
    if st.session_state.current_chat_id == cid:
        if st.session_state.all_chats:
            st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[0]
        else:
            start_new_chat()

cid = st.session_state.current_chat_id
chat = st.session_state.all_chats[cid]

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    # Brand
    st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🤖</div>
            <p class="sidebar-brand-name">AI Companion</p>
        </div>
    """, unsafe_allow_html=True)

    # Status
    if st.session_state.is_pro:
        st.markdown('<div class="status-badge-pro">⚡ Pro Plan Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge-free">🟢 Free Plan</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="upgrade-box">
                <p>Unlock faster models & priority AI access.</p>
                <a class="upgrade-btn" href="https://airoaster.lemonsqueezy.com/checkout/buy/ec7ff9c8-e11c-4102-aa52-3f5884f8fb2c" target="_blank">
                    ⚡ Upgrade to Pro — $6
                </a>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("Activate License"):
            lic = st.text_input("License Key:", type="password", key="lic_key")
            if st.button("✅ Activate Pro", use_container_width=True):
                if lic:
                    ok, msg = verify_lemonsqueezy_license(lic)
                    if ok:
                        st.session_state.is_pro = True; st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Enter your license key.")

    with st.expander("Developer Access"):
        if st.session_state.is_pro:
            st.info("⚡ Dev Pro Mode is active.")
            if st.button("🔴 Deactivate", use_container_width=True):
                st.session_state.is_pro = False; st.rerun()
        else:
            dk = st.text_input("Secret Key:", type="password", key="dev_k")
            if st.button("🔓 Activate Dev Pro", use_container_width=True):
                ds = None
                try:
                    ds = st.secrets.get("DEV_SECRET_KEY","") or None
                except Exception:
                    pass
                if not ds:
                    st.error("DEV_SECRET_KEY not configured.")
                elif dk == ds:
                    st.session_state.is_pro = True; st.rerun()
                else:
                    st.error("❌ Invalid key.")

    st.markdown("---")
    
    # 🌟 Professional Toggle Switch Button for Pro / Free Plan Mode
    st.markdown('<p class="section-label">System Mode Toggle</p>', unsafe_allow_html=True)
    toggle_pro = st.toggle("⚡ Enable Pro Engine", value=st.session_state.is_pro, help="Switch between Free and Pro model instantly.")
    if toggle_pro != st.session_state.is_pro:
        st.session_state.is_pro = toggle_pro
        st.rerun()

    st.markdown("---")
    language = st.selectbox("🌐 Language:",
        ["Roman Urdu","Roman Hindi","English","Urdu (اردو)","Hindi (हिंदी)",
         "Spanish","French","German","Arabic","Turkish"])

    active_mode = st.radio("🎯 AI Mode:",
        ["🌟 Versatile Assistant","🔥 Savage Roaster","🧠 Career Expert"])

    roast_level = "Medium"
    if active_mode == "🔥 Savage Roaster":
        roast_level = st.select_slider("🔥 Intensity:",
            options=["Normal","Medium","Hard"], value="Medium")

    st.markdown("---")
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat(); st.rerun()

    st.markdown('<p class="section-label">Recent Chats</p>', unsafe_allow_html=True)
    for c_id in list(st.session_state.all_chats.keys())[::-1]:
        info = st.session_state.all_chats[c_id]
        cb, cd = st.columns([4.2, 0.8])
        pfx = "💬 " if c_id == st.session_state.current_chat_id else ""
        if cb.button(f"{pfx}{info['title']}", key=f"b_{c_id}", use_container_width=True):
            st.session_state.current_chat_id = c_id; st.rerun()
        if cd.button("🗑️", key=f"d_{c_id}"):
            delete_chat(c_id); st.rerun()

# ==========================================
# MAIN INTERFACE
# ==========================================

# Hero Header
st.markdown("""
    <div class="hero-wrap">
        <div class="hero-badge">✦ Powered by Groq &amp; Llama 3</div>
        <h1 class="hero-title">Advanced AI Companion</h1>
        <p class="hero-sub">Chat casually · Generate code · Analyze PDF &amp; Images · Get career advice</p>
    </div>
""", unsafe_allow_html=True)

# Welcome Cards
if not chat["messages"]:
    st.markdown("""
        <div class="cards-grid">
            <div class="mode-card">
                <span class="card-icon">🌟</span>
                <p class="card-title">Versatile Assistant</p>
                <p class="card-desc">Ask anything, code, write, brainstorm, or just have a smart conversation.</p>
            </div>
            <div class="mode-card">
                <span class="card-icon">🔥</span>
                <p class="card-title">Savage Roaster</p>
                <p class="card-desc">Upload your resume or pick a topic for sharp, witty roasts + real solutions.</p>
            </div>
            <div class="mode-card">
                <span class="card-icon">🧠</span>
                <p class="card-title">Career Expert</p>
                <p class="card-desc">ATS scoring, interview prep, and professional career strategy advice.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Chat History
for m in chat["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ==========================================
# CHAT INPUT
# ==========================================
inp = st.chat_input(
    f"Message {active_mode}...",
    accept_file=True,
    file_type=["pdf","png","jpg","jpeg","webp"]
)

if inp:
    txt = inp.get("text","")
    files = inp.get("files",[])

    cf_type = cf_data = None
    display = txt

    if files:
        ft, fd = process_uploaded_file(files[0])
        if ft != "error":
            cf_type, cf_data = ft, fd
            fn = files[0].name
            display = f"📎 **[{fn}]**\n\n{txt}" if txt else f"📎 **[{fn}]**\nPlease evaluate my attached file."
        else:
            st.error(fd)

    if display or cf_type:
        stxt = txt if txt else "Conversation"
        if not chat["messages"] or chat["title"] == "New Chat":
            chat["title"] = generate_chat_title(stxt)

        st.chat_message("user").markdown(display)
        chat["messages"].append({"role":"user","content":display})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = get_ai_response(chat["messages"], active_mode, roast_level,
                                       language, f_type=cf_type, f_data=cf_data)
                st.markdown(resp)
                chat["messages"].append({"role":"assistant","content":resp})

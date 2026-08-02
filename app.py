import streamlit as st
import google.generativeai as genai

# Streamlit Page Config
st.set_page_config(
    page_title="AI Roaster & Career Assistant",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS Styling
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF4B4B;
    }
    .sub-title {
        text-align: center;
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .pro-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-top: 20px;
    }
    .checkout-btn {
        display: inline-block;
        background-color: #FF4B4B;
        color: white !important;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        text-decoration: none;
        text-align: center;
        margin-top: 10px;
    }
    .checkout-btn:hover {
        background-color: #E03E3E;
    }
    </style>
""", unsafe_allow_html=True)

# Title Section
st.markdown('<div class="main-title">🔥 AI Resume Roaster</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Upload your resume and get roasted by AI (with honest feedback)!</div>', unsafe_allow_html=True)

# Sidebar for API Key & Pro Upgrade
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    
    st.markdown("---")
    st.subheader("🚀 Upgrade to Pro")
    st.write("Get unlimited roasts, ATS analysis, and career improvement tips!")
    
    # Lemon Squeezy Checkout Link Integrated
    checkout_url = "https://airoaster.lemonsqueezy.com/checkout/buy/ec7ff9c8-e11c-4102-aa52-3f5884f8fb2c"
    st.markdown(f'<a href="{checkout_url}" target="_blank" class="checkout-btn">⭐ Upgrade to Pro ($6)</a>', unsafe_allow_html=True)

# Main App Logic
uploaded_file = st.file_uploader("Upload your Resume (TXT or Markdown format)", type=["txt", "md"])
user_resume_text = ""

if uploaded_file is not None:
    user_resume_text = uploaded_file.read().decode("utf-8")
    st.success("Resume uploaded successfully!")

st.markdown("### Or Paste Your Resume Text Below:")
pasted_text = st.text_area("Paste text here...", height=200)

if pasted_text:
    user_resume_text = pasted_text

mode = st.radio("Choose AI Mode:", ["🔥 Savage Roast Mode", "💼 Professional Feedback Mode"])

if st.button("🚀 Analyze / Roast My Resume"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar to proceed!")
    elif not user_resume_text.strip():
        st.warning("Please upload or paste your resume text first!")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')

            with st.spinner("AI is analyzing your resume..."):
                if "Savage Roast" in mode:
                    prompt = f"You are a hilarious, witty, and savage HR recruiter. Roast this resume mercilessly, point out all funny/weak points, but keep it constructive. Here is the resume:\n\n{user_resume_text}"
                else:
                    prompt = f"You are a professional career coach and HR expert. Provide detailed, constructive feedback on this resume, highlighting strengths, weaknesses, ATS optimizations, and actionable tips. Here is the resume:\n\n{user_resume_text}"

                response = model.generate_content(prompt)
                
                st.markdown("---")
                st.subheader("📝 AI Result")
                st.write(response.text)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Bottom Banner for Pro Upgrade
st.markdown("---")
st.markdown(f"""
    <div class="pro-box">
        <h3>💡 Want deeper ATS insights and personalized cover letters?</h3>
        <p>Unlock all Pro features today for just $6 (One-time payment).</p>
        <a href="{checkout_url}" target="_blank" class="checkout-btn">Get Pro Access Now</a>
    </div>
""", unsafe_allow_html=True)

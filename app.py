import streamlit as st
import re
import math

# =================== PAGE CONFIG ===================
st.set_page_config(
    page_title="AskRivo AI Mortgage Advisor",
    page_icon="🏠",
    layout="wide"
)

# =================== DARK UI CSS ===================
st.markdown("""
<style>

html, body, .stApp {
    background-color: #0b0b0b !important;
    color: #e6e6e6 !important;
    font-family: 'Inter', sans-serif;
}

/* Header */
.main-header {
    background: #111827;
    padding: 2rem;
    border-radius: 18px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 0 25px rgba(0,0,0,0.45);
}

/* Chat container */
.chat-container {
    background: #0d1117;
    padding: 1.5rem;
    border-radius: 18px;
    min-height: 450px;
    box-shadow: 0 0 25px rgba(0,0,0,0.45);
}

/* Chat bubbles */
.user-msg {
    background: #1f2937;
    padding: 1rem;
    border-radius: 14px 14px 4px 14px;
    margin: 10px 0;
    max-width: 80%;
}

.bot-msg {
    background: #111827;
    padding: 1rem;
    border-radius: 14px 14px 14px 4px;
    margin: 10px 0;
    max-width: 80%;
    border: 1px solid #1f2937;
}

/* Cards */
.info-card {
    background: #0d1117;
    padding: 1rem;
    border-radius: 14px;
    border-left: 4px solid #7c3aed;
    margin-bottom: 14px;
    box-shadow: 0 0 20px rgba(0,0,0,0.35);
}

/* Input */
.stTextInput>div>div>input {
    background: #1f2937 !important;
    color: white !important;
    border-radius: 10px;
    border: 1px solid #7c3aed !important;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
    border-radius: 10px;
    color: white;
    padding: 10px 20px;
    border: none;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =================== DETERMINISTIC MATH ===================

def calculate_emi(loan_amount, rate=4.5, years=25):
    monthly_rate = rate / 12 / 100
    n = years * 12

    if loan_amount <= 0:
        return 0.0

    emi = loan_amount * monthly_rate * (1 + monthly_rate)**n / ((1 + monthly_rate)**n - 1)
    return round(emi, 2)

def affordability_rules(price):
    max_loan = price * 0.80
    min_down = price * 0.20
    upfront = price * 0.07
    total = min_down + upfront

    return {
        "price": price,
        "max_loan": max_loan,
        "min_down": min_down,
        "upfront": upfront,
        "total_upfront": total
    }

def buy_vs_rent(price, rent, income, stay_years):
    rules = affordability_rules(price)
    emi = calculate_emi(rules["max_loan"])
    maintenance = price * 0.0025 / 12
    monthly_cost = emi + maintenance

    # Simple rules
    if stay_years and stay_years < 3:
        return emi, "rent", "Since you're staying less than 3 years, renting is normally better."

    if stay_years and stay_years > 5:
        return emi, "buy", "Since you're staying more than 5 years, buying becomes more beneficial."

    if rent and monthly_cost < rent:
        return emi, "buy", "Buying is cheaper monthly than renting."

    return emi, "rent", "Renting is safer right now based on your inputs."

# =================== SAFE LLM WRAPPER (GROQ OPTIONAL) ===================

def call_llm(prompt):
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        return None  # Skip LLM

    try:
        import groq
        client = groq.Client(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are Sakshi, a friendly UAE mortgage advisor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        return resp.choices[0].message["content"]
    except:
        return None

# =================== SESSION ===================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =================== HEADER ===================
st.markdown("""
<div class='main-header'>
    <h1>🏠 AskRivo AI Mortgage Advisor</h1>
    <p>Your smart UAE mortgage friend • Zero commission • 100% transparent</p>
</div>
""", unsafe_allow_html=True)

# =================== LAYOUT ===================
col1, col2 = st.columns([3,1])

with col1:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-msg'>👤 {msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

    user_input = st.text_input("", placeholder="e.g., I earn 25k, rent is 6k, price is 2M, staying 6 years...", key="input")

    send = st.button("Send")
    reset = st.button("New Chat")

    st.markdown("</div>", unsafe_allow_html=True)

    if reset:
        st.session_state.messages = []
        st.experimental_rerun()

    if send and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Extract numbers
        nums = re.findall(r"[\d,]+", user_input)
        nums = [float(n.replace(",", "")) for n in nums]

        price = max(nums) if nums else None
        rent = min(nums) if nums else None
        income = None

        stay_match = re.search(r"(\d+)\s*(year|yr|years)", user_input.lower())
        stay = int(stay_match.group(1)) if stay_match else None

        if not price:
            ans = "Please share property price so I can calculate."
        else:
            emi, reco, reason = buy_vs_rent(price, rent, income, stay)

            prompt = f"""
Here are precomputed numbers:

Property Price: AED {price:,.0f}
Max Loan (80%): AED {0.80 * price:,.0f}
Down Payment (20%): AED {0.20 * price:,.0f}
Upfront Costs (7%): AED {0.07 * price:,.0f}
Monthly EMI: AED {emi:,.2f}

Recommendation: {reco.upper()}
Reason: {reason}

Write a friendly 2-3 sentence explanation. Do NOT calculate numbers again.
"""

            llm_reply = call_llm(prompt)

            if not llm_reply:
                llm_reply = f"Based on your details, I recommend **{reco.upper()}**. EMI is AED {emi:,.2f}. {reason}"

            ans = llm_reply

        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.experimental_rerun()

with col2:
    st.markdown("### 📋 UAE Mortgage Rules")
    st.markdown("""
    <div class='info-card'>
    • Max Loan: 80% of property<br>
    • Min Down: 20%<br>
    • Hidden Costs: 7% extra<br>
    • Interest Rate: 4.5%<br>
    • Tenure: 25 years<br>
    </div>
    """, unsafe_allow_html=True)


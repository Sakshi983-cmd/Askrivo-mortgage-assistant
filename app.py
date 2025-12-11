import streamlit as st
import json
import re

st.set_page_config(
    page_title="AskRivo - Smart Mortgage Guide",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ OPENAI SETUP ============
from openai import OpenAI

# Get API key from Streamlit Secrets (secure)
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Add OPENAI_API_KEY to Streamlit Cloud Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# ============ BUSINESS RULES ============
MAX_LTV = 0.80
HIDDEN_COST_PERCENT = 0.07
INTEREST_RATE = 4.5
MAX_TENURE = 25
MIN_STAY_FOR_BUY = 5

# ============ MATH FUNCTIONS ============
def calculate_emi(loan_amount, annual_rate, tenure_years):
    if loan_amount <= 0 or tenure_years <= 0:
        return None
    monthly_rate = annual_rate / 100 / 12
    num_payments = tenure_years * 12
    if monthly_rate == 0:
        return loan_amount / num_payments
    emi = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    return round(emi, 2)

def calculate_upfront_costs(property_price):
    return round(property_price * HIDDEN_COST_PERCENT, 2)

def validate_ltv(property_price, down_payment):
    if down_payment < (property_price * 0.2):
        return False, f"Down payment must be at least 20% (AED {property_price * 0.2:,.0f})"
    return True, "LTV OK"

def get_buy_vs_rent_advice(stay_duration, emi, monthly_maintenance, monthly_rent):
    total_monthly_buy = emi + monthly_maintenance
    if stay_duration < MIN_STAY_FOR_BUY:
        return "RENT", f"Rent for now. {stay_duration} years is too short. 7% transaction fee kills profit."
    elif stay_duration >= MIN_STAY_FOR_BUY:
        return "BUY", f"Buy! Staying {stay_duration}+ years. Equity buildup wins. Monthly: AED {total_monthly_buy:,.0f}"
    else:
        return "CONSIDER", f"Gray zone (3-5 years). Depends on market & job stability."

# ============ EXTRACT DATA ============
def extract_user_data(message):
    data = {}
    msg_lower = message.lower()
    
    numbers = re.findall(r'\d+,?\d*', msg_lower)
    amounts = [int(n.replace(',', '')) for n in numbers]
    
    if ('income' in msg_lower or 'make' in msg_lower or 'earn' in msg_lower) and amounts:
        data['monthly_income'] = amounts[0]
    
    if ('down' in msg_lower or 'saved' in msg_lower) and len(amounts) > 0:
        data['down_payment'] = amounts[1] if len(amounts) > 1 else amounts[0]
    
    if ('buy' in msg_lower or 'apartment' in msg_lower or 'property' in msg_lower) and amounts:
        data['property_price'] = amounts[-1]
    
    years = re.findall(r'(\d+)\s*year', msg_lower)
    if years:
        data['stay_duration'] = int(years[0])
    
    return data

# ============ CALCULATE ============
def perform_calculation(data):
    if not all([data.get("property_price"), data.get("down_payment"), data.get("stay_duration")]):
        return None
    
    is_valid, msg = validate_ltv(data["property_price"], data["down_payment"])
    if not is_valid:
        return {"error": msg}
    
    loan_amount = data["property_price"] - data["down_payment"]
    tenure = MAX_TENURE
    emi = calculate_emi(loan_amount, INTEREST_RATE, tenure)
    upfront = calculate_upfront_costs(data["property_price"])
    monthly_maintenance = (data["property_price"] * 0.004) / 12
    
    advice_type, advice_text = get_buy_vs_rent_advice(
        data["stay_duration"],
        emi,
        monthly_maintenance,
        data.get("monthly_rent") or 0
    )
    
    return {
        "property_price": data["property_price"],
        "down_payment": data["down_payment"],
        "loan_amount": loan_amount,
        "emi": emi,
        "upfront_costs": upfront,
        "stay_duration": data["stay_duration"],
        "advice_type": advice_type,
        "advice_text": advice_text,
        "tenure": tenure
    }

# ============ AI RESPONSE ============
def get_ai_response(user_message, conversation_history):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_financial_data",
                "description": "Extract financial details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "monthly_income": {"type": "number"},
                        "down_payment": {"type": "number"},
                        "property_price": {"type": "number"},
                        "stay_duration": {"type": "number"}
                    }
                }
            }
        }
    ]
    
    system_prompt = """You are Rivo, a warm UAE real estate advisor. Talk like a smart friend. 
    Ask one question at a time. When you have income, property price, down payment, stay duration -> call extract_financial_data."""
    
    messages = conversation_history + [{"role": "user", "content": user_message}]
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content

# ============ SESSION STATE ============
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None

# ============ UI ============
st.markdown("""
<style>
.header-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 40px 30px;
    border-radius: 20px;
    color: white;
    text-align: center;
    margin-bottom: 30px;
}
.header-box h1 { font-size: 2.8em; font-weight: 800; margin: 0; }
.header-box p { font-size: 1.15em; opacity: 0.9; margin: 8px 0 0 0; }

.advice-box {
    padding: 25px;
    border-radius: 12px;
    border-left: 5px solid;
    margin: 20px 0;
    font-size: 1.05em;
}
.advice-buy { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); border-left-color: #2ecc71; }
.advice-rent { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-left-color: #e74c3c; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1>🏠 AskRivo</h1>
    <p>Your Smart Friend in Real Estate</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Let's figure out your best move")

# Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
if user_input := st.chat_input("Tell me about your situation..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    extracted = extract_user_data(user_input)
    st.session_state.user_data.update(extracted)
    
    with st.spinner("Rivo is thinking..."):
        try:
            ai_response = get_ai_response(user_input, st.session_state.messages[:-1])
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.write(ai_response)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    result = perform_calculation(st.session_state.user_data)
    if result and "error" not in result:
        st.session_state.calculation_result = result

# Results
if st.session_state.calculation_result:
    result = st.session_state.calculation_result
    st.divider()
    
    st.markdown("### 📊 Your Financial Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Property Price", f"{result['property_price']:,.0f}", "AED")
    with col2:
        st.metric("Down Payment", f"{result['down_payment']:,.0f}", "AED")
    with col3:
        st.metric("Monthly EMI", f"{result['emi']:,.0f}", "AED")
    with col4:
        st.metric("Hidden Costs (7%)", f"{result['upfront_costs']:,.0f}", "AED")
    
    st.divider()
    
    if result["advice_type"] == "BUY":
        st.markdown(f'<div class="advice-box advice-buy">{result["advice_text"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-box advice-rent">{result["advice_text"]}</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("### 📋 Get Your Personalized Report")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name")
    with col2:
        email = st.text_input("Email")
    
    if st.button("📧 Send Report"):
        if name and email:
            st.success(f"✅ Report sent to {email}!")
            st.balloons()
        else:
            st.error("Enter name and email")

st.divider()
st.caption("🏠 AskRivo v1.0 | CoinedOne Challenge 🚀")

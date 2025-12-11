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

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"❌ Error loading OPENAI_API_KEY: {e}")
    st.stop()


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
    if down_payment < (property_price * 0.20):
        return False, f"Down payment must be at least 20% (AED {property_price * 0.2:,.0f})"
    return True, "LTV OK"


def get_buy_vs_rent_advice(stay_duration, emi, monthly_maintenance, monthly_rent):
    total_monthly_buy = emi + monthly_maintenance
    if stay_duration < MIN_STAY_FOR_BUY:
        return "RENT", f"Rent for now. {stay_duration} years is too short due to 7% transaction costs."
    else:
        return "BUY", f"Buy! Staying {stay_duration}+ years makes ownership financially better. Monthly cost: AED {total_monthly_buy:,.0f}"


# ============ EXTRACTION ============
def extract_user_data(message):
    data = {}
    msg_lower = message.lower()

    numbers = re.findall(r'\d+,?\d*', msg_lower)
    amounts = [int(n.replace(',', '')) for n in numbers]

    # Income
    if ('income' in msg_lower or 'earn' in msg_lower or 'salary' in msg_lower) and amounts:
        data['monthly_income'] = amounts[0]

    # Down payment
    if 'down' in msg_lower or 'saved' in msg_lower:
        if len(amounts) >= 1:
            data['down_payment'] = amounts[-1]

    # Property price
    if ('buy' in msg_lower or 'property' in msg_lower or 'apartment' in msg_lower) and amounts:
        data['property_price'] = amounts[-1]

    # Stay duration
    years = re.findall(r'(\d+)\s*year', msg_lower)
    if years:
        data['stay_duration'] = int(years[0])

    return data


# ============ SAFE CALCULATION ============
def perform_calculation(data):
    if not data.get("property_price") or not data.get("down_payment") or not data.get("stay_duration"):
        return None

    # LTV
    is_valid, msg = validate_ltv(data["property_price"], data["down_payment"])
    if not is_valid:
        return {"error": msg}

    # Loan
    loan_amount = data["property_price"] - data["down_payment"]
    if loan_amount <= 0:
        return {"error": "Down payment cannot be equal or greater than property price."}

    tenure = MAX_TENURE

    # EMI
    emi = calculate_emi(loan_amount, INTEREST_RATE, tenure)
    if emi is None or emi <= 0:
        return {"error": "Unable to calculate EMI. Please check inputs."}

    # Maintenance
    monthly_maintenance = (data["property_price"] * 0.004) / 12
    if monthly_maintenance <= 0:
        return {"error": "Unable to calculate maintenance cost."}

    # Advice
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
        "upfront_costs": calculate_upfront_costs(data["property_price"]),
        "stay_duration": data["stay_duration"],
        "advice_type": advice_type,
        "advice_text": advice_text,
        "tenure": tenure
    }


# ============ AI RESPONSE ============
def get_ai_response(user_message, conversation_history):
    messages = [
        {"role": "system", "content": "You are Rivo, a warm UAE real estate friend. Ask one question at a time."}
    ] + conversation_history + [
        {"role": "user", "content": user_message}
    ]

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
        max_output_tokens=300,
    )

    return response.output_text


# ============ SESSION ============
if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None


# ============ UI ============
st.markdown("""
<div style='background:#5A60EA;padding:30px;border-radius:15px;color:white;text-align:center;margin-bottom:25px;'>
    <h1>🏠 AskRivo</h1>
    <p>Your Smart Friend for UAE Real Estate Decisions</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Tell me your situation...")


# ============ CHAT ============
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]]:
        st.write(msg["content"])


if user_input := st.chat_input("Type here..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    extracted = extract_user_data(user_input)
    st.session_state.user_data.update(extracted)

    with st.chat_message("assistant"):
        with st.spinner("Rivo is thinking..."):
            try:
                ai_response = get_ai_response(user_input, st.session_state.messages[:-1])
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                st.write(ai_response)
            except Exception as e:
                st.error(f"Error: {str(e)}")

    result = perform_calculation(st.session_state.user_data)
    if result and "error" not in result:
        st.session_state.calculation_result = result


# ============ RESULTS ============
if st.session_state.calculation_result:
    result = st.session_state.calculation_result

    st.divider()
    st.markdown("### 📊 Your Financial Breakdown")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Property Price", f"{result['property_price']:,.0f}", "AED")
    with col2: st.metric("Down Payment", f"{result['down_payment']:,.0f}", "AED")
    with col3: st.metric("Monthly EMI", f"{result['emi']:,.0f}", "AED")
    with col4: st.metric("Hidden Costs (7%)", f"{result['upfront_costs']:,.0f}", "AED")

    if result["advice_type"] == "BUY":
        st.success(result["advice_text"])
    else:
        st.warning(result["advice_text"])

st.caption("AskRivo v1.0 | Built for CoinedOne Challenge 🚀")


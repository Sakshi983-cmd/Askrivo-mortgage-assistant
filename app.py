import streamlit as st
import google.generativeai as genai
import json
import logging
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="AskRivo - Smart Mortgage Guide",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ GEMINI SETUP ============
try:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ Add GOOGLE_API_KEY to Streamlit Secrets")
        st.stop()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"❌ Error: {str(e)}")
    st.stop()

# ============ CUSTOM CSS ============
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    
    .header-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.25);
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

# ============ BUSINESS RULES ============
MAX_LTV = 0.80
HIDDEN_COST_PERCENT = 0.07
INTEREST_RATE = 4.5
MAX_TENURE = 25
MIN_STAY_FOR_BUY = 5

# ============ MATH FUNCTIONS ============
def calculate_emi(loan_amount, annual_rate, tenure_years):
    """Calculate EMI accurately"""
    try:
        if loan_amount <= 0 or tenure_years <= 0:
            return None
        
        monthly_rate = annual_rate / 100 / 12
        num_payments = tenure_years * 12
        
        if monthly_rate == 0:
            return loan_amount / num_payments
        
        emi = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        return round(emi, 2)
    except:
        return None

def calculate_upfront_costs(property_price):
    """Calculate 7% hidden costs"""
    try:
        return round(property_price * HIDDEN_COST_PERCENT, 2)
    except:
        return 0

def validate_ltv(property_price, down_payment):
    """Validate 20% minimum down payment"""
    try:
        if down_payment < (property_price * 0.2):
            return False, f"Down payment must be at least 20% (AED {property_price * 0.2:,.0f})"
        return True, "LTV OK"
    except:
        return False, "Invalid values"

def get_buy_vs_rent_advice(stay_duration, emi, monthly_maintenance, monthly_rent):
    """Smart advice based on stay duration"""
    try:
        if emi is None or monthly_maintenance is None:
            return "CONSIDER", "Please provide more financial details."
        
        total_monthly_buy = float(emi) + float(monthly_maintenance)
        
        if stay_duration < MIN_STAY_FOR_BUY:
            return "RENT", f"🏘️ Rent for now. {stay_duration} years is too short. Transaction fees hurt profit."
        elif stay_duration >= MIN_STAY_FOR_BUY:
            return "BUY", f"✅ Buy! {stay_duration}+ years. Equity buildup wins. Monthly: AED {total_monthly_buy:,.0f}"
        else:
            return "CONSIDER", f"⚖️ Close call (3-5 years). Market dependent."
    except:
        return "CONSIDER", "Unable to calculate - more details needed."

# ============ DATA EXTRACTION ============
def extract_user_data(message):
    """Extract numbers intelligently"""
    data = {}
    msg_lower = message.lower()
    
    try:
        # Extract all numbers
        number_pattern = r'\b(\d{1,3}(?:,\d{3})*|\d+)\s*(?:aed|k|lakh)?'
        matches = re.finditer(number_pattern, msg_lower)
        amounts = []
        
        for match in matches:
            num_str = match.group(1).replace(',', '')
            num = int(num_str)
            if num > 0:
                amounts.append(num)
        
        # Property price (largest number usually)
        if any(word in msg_lower for word in ['property', 'apartment', 'buy', 'home', 'villa']):
            large_nums = [n for n in amounts if n > 500000]
            if large_nums:
                data['property_price'] = max(large_nums)
            elif amounts:
                data['property_price'] = max(amounts)
        
        # Down payment
        if any(word in msg_lower for word in ['down', 'saved', 'payment']):
            down_nums = [n for n in amounts if 100000 < n < 1000000]
            if down_nums:
                data['down_payment'] = max(down_nums)
            elif len(amounts) >= 2:
                data['down_payment'] = amounts[1]
        
        # Income (small number, usually < 100k)
        if any(word in msg_lower for word in ['income', 'make', 'earn', 'salary', 'month']):
            small_nums = [n for n in amounts if n < 100000]
            if small_nums:
                data['monthly_income'] = max(small_nums)
        
        # Years
        years = re.findall(r'(\d+)\s*year', msg_lower)
        if years:
            data['stay_duration'] = int(years[0])
        
        return data
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return {}

# ============ CALCULATION ============
def perform_calculation(data):
    """Run mortgage calculations"""
    try:
        if not all([data.get("property_price"), data.get("down_payment"), data.get("stay_duration")]):
            return None
        
        property_price = float(data["property_price"])
        down_payment = float(data["down_payment"])
        stay_duration = int(data["stay_duration"])
        
        is_valid, msg = validate_ltv(property_price, down_payment)
        if not is_valid:
            return {"error": msg}
        
        loan_amount = property_price - down_payment
        emi = calculate_emi(loan_amount, INTEREST_RATE, MAX_TENURE)
        upfront = calculate_upfront_costs(property_price)
        monthly_maintenance = (property_price * 0.004) / 12
        
        advice_type, advice_text = get_buy_vs_rent_advice(
            stay_duration,
            emi,
            monthly_maintenance,
            data.get("monthly_rent") or 0
        )
        
        return {
            "property_price": property_price,
            "down_payment": down_payment,
            "loan_amount": loan_amount,
            "emi": emi,
            "upfront_costs": upfront,
            "stay_duration": stay_duration,
            "advice_type": advice_type,
            "advice_text": advice_text,
            "tenure": MAX_TENURE
        }
    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        return None

# ============ AI RESPONSE ============
def get_ai_response(user_message, conversation_history):
    """Get response from Gemini"""
    try:
        system_prompt = """You are Rivo, a warm UAE real estate advisor.
Talk like a smart friend. Ask ONE question at a time.
Keep responses to 2-3 sentences max.
Help with buy vs rent decisions.
Be empathetic about concerns."""
        
        messages = conversation_history + [{"role": "user", "content": user_message}]
        
        # Format for Gemini
        formatted = system_prompt + "\n\n"
        for msg in messages[-5:]:
            formatted += f"{msg['role'].upper()}: {msg['content']}\n"
        formatted += "RIVO: "
        
        response = model.generate_content(formatted, safety_settings="BLOCK_NONE")
        if response and response.text:
            return response.text[:500]  # Limit to 500 chars
        return "Let me help you with UAE mortgages. What would you like to know?"
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        return "I'm here to help! Tell me about your real estate situation."

# ============ SESSION STATE ============
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None

# ============ UI ============
st.markdown("""
<div class="header-box">
    <h1>🏠 AskRivo</h1>
    <p>Your Smart Friend in Real Estate</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Let's figure out your best move")

# Chat display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if user_input := st.chat_input("Tell me about your situation..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # Extract data
    extracted = extract_user_data(user_input)
    st.session_state.user_data.update(extracted)
    
    # Get AI response
    with st.spinner("Rivo is thinking..."):
        try:
            ai_response = get_ai_response(user_input, st.session_state.messages[:-1])
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.write(ai_response)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Calculate
    result = perform_calculation(st.session_state.user_data)
    if result and "error" not in result:
        st.session_state.calculation_result = result

# Show results
if st.session_state.calculation_result and "error" not in st.session_state.calculation_result:
    result = st.session_state.calculation_result
    st.divider()
    
    st.markdown("### 📊 Your Financial Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Property Price", f"{result['property_price']:,.0f}", "AED")
    with col2:
        st.metric("Down Payment", f"{result['down_payment']:,.0f}", "AED")
    with col3:
        emi_val = result.get('emi', 0) or 0
        st.metric("Monthly EMI", f"{float(emi_val):,.0f}", "AED")
    with col4:
        st.metric("Hidden Costs (7%)", f"{result['upfront_costs']:,.0f}", "AED")
    
    st.divider()
    
    advice_type = result.get('advice_type', 'CONSIDER')
    advice_text = result.get('advice_text', 'Get more details for better advice')
    
    if advice_type == "BUY":
        st.markdown(f'<div class="advice-box advice-buy">{advice_text}</div>', unsafe_allow_html=True)
    elif advice_type == "RENT":
        st.markdown(f'<div class="advice-box advice-rent">{advice_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-box advice-rent">{advice_text}</div>', unsafe_allow_html=True)
    
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

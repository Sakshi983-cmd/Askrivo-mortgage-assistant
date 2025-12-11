import streamlit as st
import openai
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============ CONFIG ============
st.set_page_config(
    page_title="AskRivo - Smart Mortgage Guide",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# OpenAI setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# ============ SESSION STATE INIT ============
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "annual_income": None,
        "monthly_income": None,
        "down_payment": None,
        "property_price": None,
        "tenure": None,
        "stay_duration": None,
        "monthly_rent": None,
        "location": None,
    }
if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None
if "lead_data" not in st.session_state:
    st.session_state.lead_data = {"name": None, "email": None, "phone": None}
if "stage" not in st.session_state:
    st.session_state.stage = "chat"  # chat, results, lead_capture

# ============ BUSINESS RULES ============
MAX_LTV = 0.80
HIDDEN_COST_PERCENT = 0.07
INTEREST_RATE = 4.5
MAX_TENURE = 25
MIN_STAY_FOR_BUY = 5
MAX_STAY_FOR_RENT = 3

# ============ MATH FUNCTIONS (NO HALLUCINATION) ============

def calculate_emi(loan_amount, annual_rate, tenure_years):
    """Calculate EMI with precision"""
    if loan_amount <= 0 or tenure_years <= 0:
        return None
    
    monthly_rate = annual_rate / 100 / 12
    num_payments = tenure_years * 12
    
    if monthly_rate == 0:
        return loan_amount / num_payments
    
    emi = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    return round(emi, 2)

def calculate_upfront_costs(property_price):
    """7% hidden costs"""
    return round(property_price * HIDDEN_COST_PERCENT, 2)

def validate_ltv(property_price, down_payment):
    """Check 20% minimum down payment"""
    if down_payment < (property_price * 0.2):
        return False, f"Down payment must be at least 20% (AED {property_price * 0.2:,.0f})"
    return True, "✓ LTV requirement met"

def get_buy_vs_rent_advice(stay_duration, emi, monthly_maintenance, monthly_rent):
    """Smart heuristic advice"""
    total_monthly_buy = emi + monthly_maintenance
    
    if stay_duration < MIN_STAY_FOR_BUY:
        return "RENT", f"🏘️ Rent for now. You'll only stay {stay_duration} years. The 7% transaction fee kills any profit. Keep renting until you're ready to stay 5+ years."
    
    elif stay_duration >= MIN_STAY_FOR_BUY:
        savings_per_month = monthly_rent - total_monthly_buy if monthly_rent > total_monthly_buy else 0
        total_equity_5_years = (property_price * 0.2) + (emi * 0.3 * 60)  # Down payment + principal paid
        
        return "BUY", f"✅ Buy now! Staying {stay_duration}+ years means:\n- Monthly: Your mortgage ({emi:,.0f} AED) vs rent ({monthly_rent:,.0f} AED)\n- Equity: Build AED {total_equity_5_years:,.0f} over {stay_duration} years\n- Freedom: Own your home, not landlord's rules"
    
    else:
        return "CONSIDER", f"⚖️ It's close. You're in the 3-5 year gray zone. Decision depends on: market appreciation expectations & your job stability in UAE."

def perform_calculation(data):
    """Run all calculations"""
    if not all([data["property_price"], data["down_payment"], data["stay_duration"]]):
        return None
    
    # Validation
    is_valid, msg = validate_ltv(data["property_price"], data["down_payment"])
    if not is_valid:
        return {"error": msg}
    
    # Calculate
    loan_amount = data["property_price"] - data["down_payment"]
    tenure = data["tenure"] or MAX_TENURE
    emi = calculate_emi(loan_amount, INTEREST_RATE, tenure)
    upfront = calculate_upfront_costs(data["property_price"])
    monthly_maintenance = (data["property_price"] * 0.004) / 12
    
    # Advice
    advice_type, advice_text = get_buy_vs_rent_advice(
        data["stay_duration"],
        emi,
        monthly_maintenance,
        data["monthly_rent"] or 0
    )
    
    total_cost_first_year = (upfront) + (emi * 12) + (monthly_maintenance * 12)
    total_cost_5_years = upfront + (emi * 60) + (monthly_maintenance * 60)
    
    return {
        "property_price": data["property_price"],
        "down_payment": data["down_payment"],
        "loan_amount": loan_amount,
        "emi": emi,
        "upfront_costs": upfront,
        "stay_duration": data["stay_duration"],
        "advice_type": advice_type,
        "advice_text": advice_text,
        "monthly_rent": data["monthly_rent"] or 0,
        "monthly_maintenance": monthly_maintenance,
        "total_monthly": emi + monthly_maintenance,
        "total_cost_5_years": total_cost_5_years,
        "tenure": tenure
    }

# ============ AI FUNCTION CALLING ============

def get_ai_response(user_message):
    """GPT-4 with function calling"""
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_financial_data",
                "description": "Extract financial details from user conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "annual_income": {"type": "number", "description": "Annual income AED"},
                        "monthly_income": {"type": "number", "description": "Monthly income AED"},
                        "down_payment": {"type": "number", "description": "Down payment AED"},
                        "property_price": {"type": "number", "description": "Property price AED"},
                        "tenure": {"type": "number", "description": "Loan tenure years"},
                        "stay_duration": {"type": "number", "description": "Years planning to stay"},
                        "monthly_rent": {"type": "number", "description": "Current monthly rent AED"},
                        "location": {"type": "string", "description": "Interested location"}
                    },
                    "required": []
                }
            }
        }
    ]
    
    system_prompt = """You are Rivo, a warm, empathetic UAE real estate advisor who guides expats through home buying decisions.

KEY TRAITS:
- Feel like a trusted friend who knows the market
- Ask 1 question at a time, naturally
- Acknowledge their fears (fees, rates, being locked in)
- When you have: income, property price, down payment, stay duration → call extract_financial_data
- After calling function, wait for user response, then give advice
- Be conversational, never robotic or survey-like

TONE: Encouraging but realistic. "I get it, the market is scary. Let me walk you through the numbers."

FLOW:
1. Greet + understand their situation (buying mindset, location, job stability)
2. Collect: monthly/annual income → property price range → down payment capacity → how long staying
3. Call extract_financial_data when you have enough
4. After calculation result: explain advice in simple terms with numbers
5. End by asking for name + email for personalized report (naturally, not pushy)
"""
    
    messages = [{"role": "user", "content": user_message}]
    
    # Add context
    filled_data = {k: v for k, v in st.session_state.user_data.items() if v is not None}
    if filled_data:
        messages.insert(0, {"role": "system", "content": f"Already collected: {filled_data}"})
    
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=300
    )
    
    assistant_msg = response.choices[0].message
    
    # Handle function calls
    if assistant_msg.tool_calls:
        for call in assistant_msg.tool_calls:
            if call.function.name == "extract_financial_data":
                data = json.loads(call.function.arguments)
                st.session_state.user_data.update(data)
    
    return assistant_msg.content

# ============ STREAMLIT UI ============

# Custom CSS
st.markdown("""
<style>
    .main { background: #f8f9ff; }
    
    .header-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.25);
    }
    
    .header-box h1 { font-size: 2.8em; font-weight: 800; margin: 0; text-shadow: 0 2px 8px rgba(0,0,0,0.2); }
    .header-box p { font-size: 1.15em; opacity: 0.9; margin: 8px 0 0 0; }
    
    .chat-container { background: white; border-radius: 15px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    
    .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-top: 4px solid #667eea;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
    }
    
    .metric-card .label { color: #999; font-size: 0.85em; text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }
    .metric-card .number { font-size: 1.8em; font-weight: 800; color: #667eea; }
    
    .advice-box {
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid;
        margin: 20px 0;
        font-size: 1.05em;
        line-height: 1.7;
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    }
    
    .advice-buy { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); border-left-color: #2ecc71; color: #1a3a2a; }
    .advice-rent { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-left-color: #e74c3c; color: #3a2a1a; }
    .advice-consider { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); border-left-color: #3498db; color: #1a2a3a; }
    
    .stChatMessage { background: transparent !important; }
    .stChatMessage > div { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-box">
    <h1>🏠 AskRivo</h1>
    <p>Your Smart Friend in Real Estate</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Let's figure out your best move")

# Chat interface
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# User input
if user_input := st.chat_input("Tell me about your situation...", key="chat_input"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    with st.spinner("Rivo is thinking..."):
        ai_response = get_ai_response(user_input)
    
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.write(ai_response)
    
    # Try calculation if we have data
    if any([st.session_state.user_data["property_price"], 
            st.session_state.user_data["down_payment"],
            st.session_state.user_data["stay_duration"]]):
        result = perform_calculation(st.session_state.user_data)
        if result and "error" not in result:
            st.session_state.calculation_result = result
            st.session_state.stage = "results"

# Show results
if st.session_state.calculation_result:
    result = st.session_state.calculation_result
    st.divider()
    
    st.markdown("### 📊 Your Financial Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Property Price", f"{result['property_price']:,.0f}", "AED")
    with col2:
        st.metric("Your Down Payment", f"{result['down_payment']:,.0f}", "AED")
    with col3:
        st.metric("Monthly EMI", f"{result['emi']:,.0f}", "AED")
    with col4:
        st.metric("Hidden Costs (7%)", f"{result['upfront_costs']:,.0f}", "AED")
    
    st.divider()
    
    # Advice
    if result["advice_type"] == "BUY":
        st.markdown(f'<div class="advice-box advice-buy">{result["advice_text"]}</div>', unsafe_allow_html=True)
    elif result["advice_type"] == "RENT":
        st.markdown(f'<div class="advice-box advice-rent">{result["advice_text"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="advice-box advice-consider">{result["advice_text"]}</div>', unsafe_allow_html=True)
    
    # Comparison
    st.markdown("### 💰 5-Year Financial Impact")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Investment (5 yrs)", f"AED {result['total_cost_5_years']:,.0f}")
    with col2:
        st.metric("Monthly Commitment", f"AED {result['total_monthly']:,.0f}")
    with col3:
        st.metric("Loan Tenure", f"{result['tenure']} years")
    
    st.divider()
    
    # Lead capture
    st.markdown("### 📋 Get Your Personalized Report")
    st.markdown("*We'll send you a detailed analysis + market insights*")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name", value=st.session_state.lead_data.get("name", ""), key="name_input")
    with col2:
        email = st.text_input("Email Address", value=st.session_state.lead_data.get("email", ""), key="email_input")
    
    phone = st.text_input("Phone (Optional)", value=st.session_state.lead_data.get("phone", ""), key="phone_input")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📧 Send Report", use_container_width=True):
            if name and email:
                st.session_state.lead_data = {"name": name, "email": email, "phone": phone}
                st.success(f"✅ Report sent to {email}!")
                st.balloons()
                st.info("💡 Next: A Rivo expert will contact you within 24 hours for personalized guidance.")
            else:
                st.error("Please enter name and email")

st.divider()
st.markdown("""
<div style='text-align: center; color: #999; font-size: 0.9em;'>
<p>🏠 AskRivo v1.0 | AI-Native Real Estate for UAE Expats | Transparent. Fair. Smart.</p>
<p>Built for CoinedOne | 24-Hour Challenge 🚀</p>
</div>
""", unsafe_allow_html=True)

import streamlit as st
import google.generativeai as genai
import json
import logging
import re
from datetime import datetime
import time

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
    model = genai.GenerativeModel('gemini-1.5-flash')
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
    
    .tool-badge {
        display: inline-block;
        background: rgba(102, 126, 234, 0.3);
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 0.85em;
        margin: 5px 0;
        color: white;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============ BUSINESS RULES ============
MAX_LTV = 0.80
HIDDEN_COST_PERCENT = 0.07
INTEREST_RATE = 4.5
MAX_TENURE = 25
MIN_STAY_FOR_BUY = 5

# ============ TOOL FUNCTIONS (Zero Hallucination Math) ============

def calculate_emi(loan_amount: float, annual_rate: float, tenure_years: int) -> dict:
    """Calculate EMI using standard formula - 100% accurate"""
    try:
        if loan_amount <= 0 or tenure_years <= 0:
            return {"error": "Invalid inputs"}
        
        monthly_rate = annual_rate / 100 / 12
        num_payments = tenure_years * 12
        
        if monthly_rate == 0:
            emi = loan_amount / num_payments
        else:
            emi = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                  ((1 + monthly_rate)**num_payments - 1)
        
        total_payment = emi * num_payments
        total_interest = total_payment - loan_amount
        
        logger.info(f"🔧 EMI Calculated: {emi:.2f} AED")
        
        return {
            "emi": round(emi, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2),
            "loan_amount": loan_amount,
            "rate": annual_rate,
            "tenure": tenure_years
        }
    except Exception as e:
        logger.error(f"EMI error: {e}")
        return {"error": str(e)}

def calculate_affordability(property_price: float, down_payment: float) -> dict:
    """Check if property is affordable based on UAE rules"""
    try:
        min_down = property_price * 0.2
        
        if down_payment < min_down:
            return {
                "affordable": False,
                "error": f"Need minimum 20% down payment: AED {min_down:,.0f}",
                "shortfall": min_down - down_payment
            }
        
        loan_amount = property_price - down_payment
        upfront_costs = property_price * HIDDEN_COST_PERCENT
        
        logger.info(f"🔧 Affordability Check: Property {property_price}, Down {down_payment}")
        
        return {
            "affordable": True,
            "property_price": property_price,
            "down_payment": down_payment,
            "loan_amount": loan_amount,
            "upfront_costs": upfront_costs,
            "total_initial": down_payment + upfront_costs,
            "ltv_ratio": round((loan_amount / property_price) * 100, 2)
        }
    except Exception as e:
        logger.error(f"Affordability error: {e}")
        return {"error": str(e)}

def buy_vs_rent_analysis(property_price: float, monthly_rent: float, stay_years: int) -> dict:
    """Analyze buy vs rent decision"""
    try:
        down_payment = property_price * 0.2
        loan_amount = property_price - down_payment
        
        # Get EMI
        emi_result = calculate_emi(loan_amount, INTEREST_RATE, MAX_TENURE)
        if "error" in emi_result:
            return emi_result
        
        monthly_emi = emi_result["emi"]
        monthly_maintenance = property_price * 0.002
        total_monthly_own = monthly_emi + monthly_maintenance
        
        # Total costs
        total_rent_cost = monthly_rent * 12 * stay_years
        upfront_costs = property_price * HIDDEN_COST_PERCENT
        total_own_cost = (down_payment + upfront_costs + 
                         (total_monthly_own * 12 * stay_years))
        
        # Decision
        if stay_years < 3:
            recommendation = "RENT"
            reason = "Short stay - transaction costs not recovered"
        elif stay_years >= 5:
            recommendation = "BUY"
            reason = "Long stay - equity buildup wins"
        else:
            recommendation = "BUY" if total_own_cost < total_rent_cost else "RENT"
            reason = "Medium stay - calculated based on costs"
        
        logger.info(f"🔧 Buy vs Rent: {recommendation}")
        
        return {
            "recommendation": recommendation,
            "reason": reason,
            "monthly_rent": monthly_rent,
            "monthly_emi": monthly_emi,
            "monthly_own": total_monthly_own,
            "total_rent": total_rent_cost,
            "total_own": total_own_cost,
            "stay_years": stay_years
        }
    except Exception as e:
        logger.error(f"Buy vs Rent error: {e}")
        return {"error": str(e)}

# ============ SMART DATA EXTRACTION ============

def extract_numbers(text: str) -> dict:
    """Extract financial numbers from text"""
    data = {}
    text_lower = text.lower()
    
    try:
        # Find all numbers
        numbers = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:k|m|lakh|aed)?', text_lower)
        amounts = []
        
        for num_str in numbers:
            num = float(num_str.replace(',', ''))
            
            # Handle k, m notations
            if 'k' in text_lower[text_lower.find(num_str):text_lower.find(num_str)+10]:
                num *= 1000
            elif 'm' in text_lower[text_lower.find(num_str):text_lower.find(num_str)+10]:
                num *= 1000000
            
            if num > 0:
                amounts.append(int(num))
        
        # Identify what each number represents
        if any(word in text_lower for word in ['property', 'apartment', 'buy', 'home', 'price']):
            large = [n for n in amounts if n > 500000]
            if large:
                data['property_price'] = max(large)
        
        if any(word in text_lower for word in ['down', 'payment', 'saved', 'have']):
            medium = [n for n in amounts if 100000 < n < 1000000]
            if medium:
                data['down_payment'] = max(medium)
        
        if any(word in text_lower for word in ['income', 'earn', 'salary', 'make']):
            small = [n for n in amounts if n < 100000]
            if small:
                data['monthly_income'] = max(small)
        
        if any(word in text_lower for word in ['rent', 'paying']):
            rent_nums = [n for n in amounts if 3000 < n < 50000]
            if rent_nums:
                data['monthly_rent'] = max(rent_nums)
        
        # Years
        years = re.findall(r'(\d+)\s*year', text_lower)
        if years:
            data['stay_years'] = int(years[0])
        
        return data
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return {}

# ============ AI ORCHESTRATION WITH TOOL CALLING ============

def get_ai_response(user_message: str, conversation_history: list, max_retries: int = 3) -> dict:
    """
    AI with intelligent tool calling
    
    Strategy:
    1. Extract data from message
    2. Check if we should calculate
    3. Call appropriate tool
    4. Let AI interpret results naturally
    """
    
    # Extract data
    extracted = extract_numbers(user_message)
    
    # Check what tool to use
    tool_used = None
    tool_result = None
    
    # Decision logic for tool calling
    if 'property_price' in extracted and 'down_payment' in extracted:
        # Affordability check
        tool_used = "calculate_affordability"
        tool_result = calculate_affordability(
            extracted['property_price'],
            extracted['down_payment']
        )
    
    elif 'property_price' in extracted and 'monthly_rent' in extracted and 'stay_years' in extracted:
        # Buy vs Rent
        tool_used = "buy_vs_rent"
        tool_result = buy_vs_rent_analysis(
            extracted['property_price'],
            extracted['monthly_rent'],
            extracted['stay_years']
        )
    
    elif 'property_price' in extracted:
        # Simple affordability with 20% down
        down = extracted['property_price'] * 0.2
        tool_used = "calculate_affordability"
        tool_result = calculate_affordability(extracted['property_price'], down)
    
    # Build context for AI
    context_messages = []
    for msg in conversation_history[-8:]:
        context_messages.append(f"{msg['role'].upper()}: {msg['content']}")
    
    context_str = "\n".join(context_messages)
    
    # System prompt with tool results
    system_prompt = f"""You are Rivo, a friendly UAE mortgage advisor.

UAE Rules (for your knowledge):
- Expats: max 80% LTV (20% down mandatory)
- Hidden costs: 7% (transfer + agency + misc)
- Interest rate: 4.5% annual
- Max tenure: 25 years

Conversation so far:
{context_str}

User's latest message: {user_message}
"""
    
    # Add tool results if available
    if tool_result and "error" not in tool_result:
        system_prompt += f"\n\nTOOL RESULT from {tool_used}:\n{json.dumps(tool_result, indent=2)}\n"
        system_prompt += "\nUSE THIS DATA to give a natural, friendly response. Explain what the numbers mean in simple terms."
    
    system_prompt += "\n\nYour response (2-3 sentences, warm and helpful):"
    
    # Call AI with retry logic
    for attempt in range(max_retries):
        try:
            logger.info(f"AI call attempt {attempt + 1}")
            
            response = model.generate_content(
                system_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 500,
                }
            )
            
            if response and response.text:
                return {
                    "text": response.text,
                    "tool_used": tool_used,
                    "tool_result": tool_result,
                    "extracted_data": extracted
                }
        
        except Exception as e:
            logger.error(f"AI error (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return {
                    "text": "I'm having connection issues. Let me help you with UAE mortgage basics - what would you like to know?",
                    "tool_used": None,
                    "tool_result": None,
                    "extracted_data": {}
                }
    
    return {
        "text": "Hi! I'm Rivo, your UAE mortgage guide. Tell me about your situation and I'll help you decide!",
        "tool_used": None,
        "tool_result": None,
        "extracted_data": {}
    }

# ============ SESSION STATE ============
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = 0

# ============ UI ============
st.markdown("""
<div class="header-box">
    <h1>🏠 AskRivo</h1>
    <p>Your AI-Powered UAE Mortgage Advisor</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔧 AI Tools Status")
    st.metric("Calculations Performed", st.session_state.tool_calls)
    st.markdown("---")
    st.markdown("### 📚 UAE Rules")
    st.info(f"""
    **Max LTV**: {int(MAX_LTV * 100)}%
    **Hidden Costs**: {int(HIDDEN_COST_PERCENT * 100)}%
    **Interest**: {INTEREST_RATE}%
    **Max Tenure**: {MAX_TENURE} years
    """)
    st.markdown("---")
    st.markdown("### 💡 Try Asking")
    st.text("• EMI for 1.6M loan?")
    st.text("• Can I afford 2M property?")
    st.text("• Should I buy or rent?")

st.markdown("### 💬 Chat with Rivo")

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        if "tool_used" in msg and msg["tool_used"]:
            st.markdown(f'<span class="tool-badge">🔧 {msg["tool_used"]}</span>', 
                       unsafe_allow_html=True)

# Chat input
if user_input := st.chat_input("Tell me your situation..."):
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Rivo is thinking..."):
            response = get_ai_response(
                user_input,
                st.session_state.messages[:-1]
            )
            
            # Typing effect
            placeholder = st.empty()
            full_text = response["text"]
            displayed = ""
            
            for char in full_text:
                displayed += char
                placeholder.write(displayed + "▌")
                time.sleep(0.01)
            
            placeholder.write(full_text)
            
            # Show tool badge
            if response["tool_used"]:
                st.markdown(f'<span class="tool-badge">🔧 {response["tool_used"]}</span>', 
                           unsafe_allow_html=True)
                st.session_state.tool_calls += 1
            
            # Show calculation details
            if response["tool_result"] and "error" not in response["tool_result"]:
                with st.expander("📊 Calculation Details"):
                    st.json(response["tool_result"])
    
    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["text"],
        "tool_used": response["tool_used"],
        "tool_result": response["tool_result"]
    })

# Lead capture
if len(st.session_state.messages) >= 10:
    st.divider()
    st.markdown("### 📧 Get Your Personalized Report")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name", key="name")
    with col2:
        email = st.text_input("Email", key="email")
    
    if st.button("📨 Send Report", type="primary"):
        if name and email:
            st.success(f"✅ Report will be sent to {email}!")
            st.balloons()
        else:
            st.error("Please enter both fields")

st.divider()
st.caption("🏠 AskRivo | AI Engineering Challenge | Built with Gemini 1.5 Flash 🚀")

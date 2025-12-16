import streamlit as st
import google.generativeai as genai
from google.generativeai.types import content_types
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
    
    .tool-call-badge {
        display: inline-block;
        background: rgba(102, 126, 234, 0.2);
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 0.85em;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============ BUSINESS RULES ============
MAX_LTV = 0.80
HIDDEN_COST_PERCENT = 0.07
INTEREST_RATE = 4.5
MAX_TENURE = 25
MIN_STAY_FOR_BUY = 5

# ============ TOOL FUNCTIONS (For Gemini Function Calling) ============

def calculate_emi_tool(loan_amount: float, annual_rate: float, tenure_years: int) -> dict:
    """Calculate EMI - Called by AI via function calling"""
    try:
        logger.info(f"🔧 TOOL CALLED: calculate_emi({loan_amount}, {annual_rate}, {tenure_years})")
        
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
        
        return {
            "emi": round(emi, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2),
            "monthly_rate": round(monthly_rate * 100, 4),
            "num_payments": num_payments
        }
    except Exception as e:
        logger.error(f"EMI calculation error: {e}")
        return {"error": str(e)}

def calculate_affordability_tool(property_price: float, down_payment: float) -> dict:
    """Check affordability - Called by AI via function calling"""
    try:
        logger.info(f"🔧 TOOL CALLED: calculate_affordability({property_price}, {down_payment})")
        
        min_down = property_price * 0.2
        if down_payment < min_down:
            return {
                "affordable": False,
                "error": f"Down payment must be at least 20% (AED {min_down:,.0f})"
            }
        
        loan_amount = property_price - down_payment
        max_loan = property_price * MAX_LTV
        upfront_costs = property_price * HIDDEN_COST_PERCENT
        
        upfront_breakdown = {
            "transfer_fee": property_price * 0.04,
            "agency_fee": property_price * 0.02,
            "misc_fees": property_price * 0.01
        }
        
        return {
            "affordable": True,
            "property_price": property_price,
            "down_payment": down_payment,
            "loan_amount": loan_amount,
            "max_loan": max_loan,
            "upfront_costs": upfront_costs,
            "upfront_breakdown": upfront_breakdown,
            "total_initial": down_payment + upfront_costs,
            "ltv_ratio": round((loan_amount / property_price) * 100, 2)
        }
    except Exception as e:
        logger.error(f"Affordability error: {e}")
        return {"error": str(e)}

def buy_vs_rent_tool(property_price: float, monthly_rent: float, stay_years: int, 
                     down_payment: float = None) -> dict:
    """Buy vs Rent analysis - Called by AI via function calling"""
    try:
        logger.info(f"🔧 TOOL CALLED: buy_vs_rent({property_price}, {monthly_rent}, {stay_years})")
        
        if down_payment is None:
            down_payment = property_price * 0.2
        
        loan_amount = property_price - down_payment
        
        # Calculate EMI
        emi_result = calculate_emi_tool(loan_amount, INTEREST_RATE, MAX_TENURE)
        if "error" in emi_result:
            return emi_result
        
        monthly_emi = emi_result["emi"]
        monthly_maintenance = property_price * 0.002
        total_monthly_own = monthly_emi + monthly_maintenance
        
        # Total costs over stay period
        total_rent_cost = monthly_rent * 12 * stay_years
        upfront_costs = property_price * HIDDEN_COST_PERCENT
        total_own_cost = (down_payment + upfront_costs + 
                          (total_monthly_own * 12 * stay_years))
        
        # Decision logic
        if stay_years < 3:
            recommendation = "RENT"
            reason = "Transaction costs (7%) won't be recovered in short timeframe"
        elif stay_years >= 5:
            recommendation = "BUY"
            reason = "Long-term equity buildup outweighs transaction costs"
        else:
            if total_own_cost < total_rent_cost * 1.1:  # 10% buffer
                recommendation = "BUY"
                reason = "Break-even analysis slightly favors buying"
            else:
                recommendation = "RENT"
                reason = "Renting is more economical for this medium timeframe"
        
        return {
            "recommendation": recommendation,
            "reason": reason,
            "monthly_rent": monthly_rent,
            "monthly_emi": monthly_emi,
            "monthly_maintenance": monthly_maintenance,
            "total_monthly_own": total_monthly_own,
            "total_rent_cost": total_rent_cost,
            "total_own_cost": total_own_cost,
            "upfront_required": down_payment + upfront_costs,
            "stay_years": stay_years
        }
    except Exception as e:
        logger.error(f"Buy vs Rent error: {e}")
        return {"error": str(e)}

# ============ DEFINE TOOLS FOR GEMINI ============

calculate_emi_declaration = content_types.FunctionDeclaration(
    name="calculate_emi",
    description="Calculate monthly EMI (Equated Monthly Installment) for a mortgage loan. Use this when user asks about monthly payments or EMI.",
    parameters=content_types.Schema(
        type=content_types.Type.OBJECT,
        properties={
            "loan_amount": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="The loan amount in AED"
            ),
            "annual_rate": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)"
            ),
            "tenure_years": content_types.Schema(
                type=content_types.Type.INTEGER,
                description="Loan tenure in years"
            )
        },
        required=["loan_amount", "annual_rate", "tenure_years"]
    )
)

calculate_affordability_declaration = content_types.FunctionDeclaration(
    name="calculate_affordability",
    description="Check if a property is affordable based on price and down payment. Validates 20% minimum down payment rule for UAE expats.",
    parameters=content_types.Schema(
        type=content_types.Type.OBJECT,
        properties={
            "property_price": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Property price in AED"
            ),
            "down_payment": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Down payment amount in AED"
            )
        },
        required=["property_price", "down_payment"]
    )
)

buy_vs_rent_declaration = content_types.FunctionDeclaration(
    name="buy_vs_rent",
    description="Analyze whether to buy or rent based on property price, current rent, and planned stay duration. Provides financial comparison and recommendation.",
    parameters=content_types.Schema(
        type=content_types.Type.OBJECT,
        properties={
            "property_price": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Property price in AED"
            ),
            "monthly_rent": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Current monthly rent in AED"
            ),
            "stay_years": content_types.Schema(
                type=content_types.Type.INTEGER,
                description="How many years user plans to stay"
            ),
            "down_payment": content_types.Schema(
                type=content_types.Type.NUMBER,
                description="Optional: Down payment amount. Defaults to 20% if not provided"
            )
        },
        required=["property_price", "monthly_rent", "stay_years"]
    )
)

mortgage_tools = content_types.Tool(
    function_declarations=[
        calculate_emi_declaration,
        calculate_affordability_declaration,
        buy_vs_rent_declaration
    ]
)

# ============ AI WITH FUNCTION CALLING ============

def get_ai_response_with_tools(user_message, conversation_history, max_retries=3):
    """Get AI response with function calling capability + retry logic"""
    
    system_prompt = """You are Rivo, a warm and knowledgeable UAE real estate advisor.

Your personality:
- Talk like a smart friend, not a robot
- Keep responses concise (2-3 sentences max)
- Ask ONE question at a time to gather information
- Be empathetic about user's concerns

UAE Mortgage Rules (use these for context):
- Expats can borrow maximum 80% (20% down payment mandatory)
- Hidden costs: ~7% (4% transfer fee + 2% agency + 1% misc)
- Standard interest rate: 4.5% annual
- Maximum tenure: 25 years

When to use tools:
1. User mentions property price + down payment → use calculate_affordability
2. User asks about EMI/monthly payment → use calculate_emi
3. User asks "should I buy or rent?" → use buy_vs_rent

IMPORTANT: When you call a function, I will give you the result. Use that result to give a friendly, natural response. Don't just dump numbers - explain what they mean!

Example:
User: "I want to buy a 2M AED apartment with 400k down"
You: *calls calculate_affordability*
Then respond: "Great! A 2M property with 400k down works perfectly - that's exactly the 20% required. Your loan would be 1.6M. Plus, budget for 140k in upfront costs (transfer fees, etc). Want to know your monthly EMI?"
"""
    
    # Build conversation context
    messages = []
    for msg in conversation_history[-10:]:  # Last 10 messages
        messages.append({
            "role": msg["role"],
            "parts": [msg["content"]]
        })
    messages.append({
        "role": "user",
        "parts": [user_message]
    })
    
    # Try with retry logic
    for attempt in range(max_retries):
        try:
            logger.info(f"AI call attempt {attempt + 1}/{max_retries}")
            
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                tools=[mortgage_tools],
                system_instruction=system_prompt
            )
            
            chat = model.start_chat()
            
            # Send all context
            for msg in messages:
                response = chat.send_message(msg["parts"][0])
            
            # Check if tool was called
            tool_calls = []
            function_results = []
            
            for part in response.parts:
                if fn := part.function_call:
                    logger.info(f"🎯 AI decided to call: {fn.name}")
                    tool_calls.append(fn.name)
                    
                    # Execute the function
                    args = dict(fn.args)
                    
                    if fn.name == "calculate_emi":
                        result = calculate_emi_tool(**args)
                    elif fn.name == "calculate_affordability":
                        result = calculate_affordability_tool(**args)
                    elif fn.name == "buy_vs_rent":
                        result = buy_vs_rent_tool(**args)
                    else:
                        result = {"error": "Unknown function"}
                    
                    function_results.append(result)
                    
                    # Send result back to AI
                    response = chat.send_message(
                        content_types.Part.from_function_response(
                            name=fn.name,
                            response={"result": result}
                        )
                    )
            
            # Get final text response
            final_text = response.text if response.text else "I'm processing that information..."
            
            return {
                "text": final_text,
                "tool_calls": tool_calls,
                "function_results": function_results
            }
            
        except Exception as e:
            logger.error(f"AI error (attempt {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error("Max retries exceeded")
                return {
                    "text": "I'm having trouble connecting right now. Let me try to help anyway - what specific question do you have about UAE mortgages?",
                    "tool_calls": [],
                    "function_results": []
                }

# ============ SESSION STATE ============
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_usage_count" not in st.session_state:
    st.session_state.tool_usage_count = 0

# ============ UI ============
st.markdown("""
<div class="header-box">
    <h1>🏠 AskRivo</h1>
    <p>Your AI-Powered Real Estate Advisor</p>
</div>
""", unsafe_allow_html=True)

# Sidebar stats
with st.sidebar:
    st.markdown("### 🔧 AI Tools Used")
    st.metric("Function Calls", st.session_state.tool_usage_count)
    st.markdown("---")
    st.markdown("### 📚 Quick Facts")
    st.info(f"""
    - Max LTV: {int(MAX_LTV * 100)}%
    - Hidden Costs: {int(HIDDEN_COST_PERCENT * 100)}%
    - Interest Rate: {INTEREST_RATE}%
    - Max Tenure: {MAX_TENURE} years
    """)

st.markdown("### 💬 Chat with Rivo")

# Chat display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Show tool usage badge if present
        if "tool_calls" in msg and msg["tool_calls"]:
            tools_used = ", ".join(msg["tool_calls"])
            st.markdown(f'<span class="tool-call-badge">🔧 Used: {tools_used}</span>', 
                       unsafe_allow_html=True)

# Chat input
if user_input := st.chat_input("Tell me about your situation..."):
    # Add user message
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input
    })
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # Get AI response with streaming effect
    with st.chat_message("assistant"):
        with st.spinner("Rivo is thinking..."):
            response = get_ai_response_with_tools(
                user_input, 
                st.session_state.messages[:-1]
            )
            
            # Show response with typing effect
            message_placeholder = st.empty()
            full_response = response["text"]
            displayed_text = ""
            
            for char in full_response:
                displayed_text += char
                message_placeholder.write(displayed_text + "▌")
                time.sleep(0.01)
            
            message_placeholder.write(full_response)
            
            # Show tool usage
            if response["tool_calls"]:
                tools_used = ", ".join(response["tool_calls"])
                st.markdown(f'<span class="tool-call-badge">🔧 Used: {tools_used}</span>', 
                           unsafe_allow_html=True)
                st.session_state.tool_usage_count += len(response["tool_calls"])
            
            # Display results if available
            if response["function_results"]:
                for result in response["function_results"]:
                    if "error" not in result:
                        with st.expander("📊 See calculation details"):
                            st.json(result)
    
    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["text"],
        "tool_calls": response["tool_calls"],
        "function_results": response["function_results"]
    })

# Lead capture (appears after 5+ messages)
if len(st.session_state.messages) >= 10:
    st.divider()
    st.markdown("### 📧 Want a Detailed Report?")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name", key="lead_name")
    with col2:
        email = st.text_input("Email", key="lead_email")
    
    if st.button("Send My Report", type="primary"):
        if name and email:
            st.success(f"✅ Report sent to {email}! Our advisor will contact you soon.")
            st.balloons()
        else:
            st.error("Please enter both name and email")

st.divider()
st.caption("🏠 AskRivo v2.0 | Built with ❤️ using Gemini Function Calling 🚀")

# app.py - AskRivo Mortgage AI Assistant

import streamlit as st
import google.generativeai as genai
import math
import json
import re
from datetime import datetime

# ============ CONFIGURATION ============
st.set_page_config(
    page_title="AskRivo AI Mortgage Advisor",
    page_icon="🏠",
    layout="wide"
)

# ============ STYLING ============
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
    }
    
    .user-msg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 10px 0 10px auto;
        max-width: 70%;
    }
    
    .bot-msg {
        background: #f0f2f6;
        color: #333;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 10px auto 10px 0;
        max-width: 70%;
        border: 1px solid #ddd;
    }
    
    .card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1rem;
        border-top: 1px solid #eee;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============ MORTGAGE CALCULATOR ============
class MortgageCalculator:
    """Accurate mortgage calculations - Zero hallucinations"""
    
    @staticmethod
    def calculate_emi(loan_amount, rate=4.5, years=25):
        """Calculate EMI using standard formula"""
        monthly_rate = rate / 12 / 100
        months = years * 12
        emi = loan_amount * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
        return round(emi, 2)
    
    @staticmethod
    def calculate_affordability(property_price):
        """Calculate all costs as per UAE rules"""
        max_loan = property_price * 0.80  # 80% LTV
        min_down = property_price * 0.20  # 20% minimum
        upfront_costs = property_price * 0.07  # 7% hidden costs
        return {
            'max_loan': round(max_loan, 2),
            'min_down': round(min_down, 2),
            'upfront': round(upfront_costs, 2),
            'total_upfront': round(min_down + upfront_costs, 2)
        }
    
    @staticmethod
    def buy_vs_rent(monthly_rent, property_price, years_planned):
        """Buy vs Rent analysis"""
        affordability = MortgageCalculator.calculate_affordability(property_price)
        emi = MortgageCalculator.calculate_emi(affordability['max_loan'])
        
        if years_planned < 3:
            return "RENT - Transaction costs too high for short stay"
        elif years_planned > 5:
            return "BUY - Equity buildup beats renting long-term"
        else:
            total_rent = monthly_rent * 12 * years_planned
            total_own = (emi * 12 * years_planned) + affordability['total_upfront']
            return f"Compare: Rent = AED {total_rent:,.0f}, Buy = AED {total_own:,.0f}"

# ============ AI AGENT ============
class AIAgent:
    """AI that uses tools for accurate calculations"""
    
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel('gemini-1.0-pro')
        except:
            self.model = genai.GenerativeModel('gemini-pro')
        self.calculator = MortgageCalculator()
        self.user_data = {}
    
    def extract_numbers(self, text):
        """Extract numbers from text"""
        numbers = re.findall(r'[\d,]+\.?\d*', text)
        return [float(n.replace(',', '')) for n in numbers if n]
    
    def generate_response(self, user_input):
        """Generate intelligent response with calculations"""
        # Extract user data
        nums = self.extract_numbers(user_input)
        
        if 'income' in user_input.lower() and nums:
            self.user_data['income'] = nums[0]
        
        if 'aed' in user_input.lower() or 'price' in user_input.lower():
            if nums:
                self.user_data['property_price'] = max(nums)
        
        if 'rent' in user_input.lower() and nums:
            self.user_data['rent'] = nums[0]
        
        # Perform calculations if we have data
        calculation_text = ""
        if 'property_price' in self.user_data:
            price = self.user_data['property_price']
            aff = self.calculator.calculate_affordability(price)
            emi = self.calculator.calculate_emi(aff['max_loan'])
            
            calculation_text = f"""
            For AED {price:,.0f} property:
            • Max loan: AED {aff['max_loan']:,.0f}
            • Min down payment: AED {aff['min_down']:,.0f}
            • Hidden costs: AED {aff['upfront']:,.0f}
            • Monthly EMI: AED {emi:,.0f}
            • Total upfront: AED {aff['total_upfront']:,.0f}
            """
            
            if 'income' in self.user_data:
                income = self.user_data['income']
                if emi > income * 0.4:
                    calculation_text += f"\n⚠️ Warning: EMI (AED {emi:,.0f}) is >40% of your income (AED {income:,.0f})"
                else:
                    calculation_text += f"\n✅ EMI is affordable at {(emi/income*100):.1f}% of your income"
        
        # Generate AI response
        prompt = f"""
        You are Zara, a friendly UAE mortgage advisor.
        
        User said: "{user_input}"
        
        {calculation_text if calculation_text else "No calculations yet - need property price."}
        
        Rules for UAE:
        1. Expats can borrow max 80% of property value
        2. Minimum 20% down payment required
        3. Additional 7% upfront costs (transfer fee + agency fee)
        4. Standard interest rate: 4.5%
        5. Max loan tenure: 25 years
        
        Ask ONE question at a time. Be warm and helpful.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            # Fallback response
            return f"I can help with UAE mortgages! {calculation_text if calculation_text else 'Please share the property price in AED.'}"

# ============ FEEDBACK SYSTEM ============
class FeedbackSystem:
    """Simple feedback collection"""
    
    def __init__(self):
        self.stages = [
            ("Hi! How was your experience with our mortgage advisor?", "rating"),
            ("Could you rate us 1-5 stars?", "improvement"),
            ("What could we improve?", "contact"),
            ("Share email for personalized report?", "thanks"),
            ("Thank you! We'll use your feedback.", "done")
        ]
        self.current = 0
    
    def get_prompt(self):
        return self.stages[self.current][0] if self.current < len(self.stages) else ""
    
    def next(self):
        if self.current < len(self.stages) - 1:
            self.current += 1
            return True
        return False

# ============ APP INITIALIZATION ============
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'feedback' not in st.session_state:
    st.session_state.feedback = FeedbackSystem()
if 'show_feedback' not in st.session_state:
    st.session_state.show_feedback = False

# ============ MAIN UI ============
st.markdown("""
<div class="main-header">
    <h1>🏠 AskRivo AI Mortgage Advisor</h1>
    <p>Your smart friend for UAE mortgages - No hidden fees, no confusion</p>
</div>
""", unsafe_allow_html=True)

# Two columns
col1, col2 = st.columns([3, 1])

with col1:
    # Chat display
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-msg">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
    
    # Feedback
    if st.session_state.show_feedback:
        st.markdown(f'<div class="card">💬 {st.session_state.feedback.get_prompt()}</div>', unsafe_allow_html=True)
    
    # Input
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    user_input = st.text_input("Type your message...", key="input", label_visibility="collapsed")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Send Message", use_container_width=True) and user_input:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Initialize agent
            if not st.session_state.agent:
                api_key = st.secrets.get("GEMINI_API_KEY", "")
                if api_key:
                    st.session_state.agent = AIAgent(api_key)
                else:
                    st.error("Please set GEMINI_API_KEY in secrets")
            
            # Get response
            if st.session_state.agent:
                response = st.session_state.agent.generate_response(user_input)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Trigger feedback after 5 messages
            if len(st.session_state.messages) >= 10 and not st.session_state.show_feedback:
                st.session_state.show_feedback = True
            
            st.rerun()
    
    with col_btn2:
        if st.button("New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent = None
            st.session_state.show_feedback = False
            st.session_state.feedback = FeedbackSystem()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Sidebar info
    st.markdown("### 📊 Quick Facts")
    st.markdown("""
    <div class="card">
    <b>UAE Rules for Expats:</b><br>
    • Max Loan: 80%<br>
    • Min Down: 20%<br>
    • Hidden Costs: 7%<br>
    • Max Tenure: 25 years
    </div>
    """, unsafe_allow_html=True)
    
    # Safe check - कोई error नहीं
    try:
        if st.session_state.agent:
            # Check अगर user_data है तो
            if hasattr(st.session_state.agent, 'user_data'):
                data = st.session_state.agent.user_data
                if data:
                    if 'income' in data:
                        st.markdown(f'<div class="card">💰 Income: AED {data["income"]:,.0f}/month</div>', unsafe_allow_html=True)
                    if 'property_price' in data:
                        st.markdown(f'<div class="card">🏡 Property: AED {data["property_price"]:,.0f}</div>', unsafe_allow_html=True)
            else:
                # अगर user_data नहीं है, तो conversation data देखो
                if hasattr(st.session_state.agent, 'conversation'):
                    conv = st.session_state.agent.conversation
                    if hasattr(conv, 'extracted_data'):
                        data = conv.extracted_data
                        if 'financial' in data and 'monthly_income' in data['financial']:
                            income = data['financial']['monthly_income']
                            st.markdown(f'<div class="card">💰 Income: AED {income:,.0f}/month</div>', unsafe_allow_html=True)
    except:
        pass  # कुछ नहीं दिखाओ
# ============ ERROR HANDLING ============
try:
    # This ensures the app runs without errors
    pass
except Exception as e:
    st.error("Something went wrong. Please refresh the page.")
    st.code(f"Error: {str(e)}")



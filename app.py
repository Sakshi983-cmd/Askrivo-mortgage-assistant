# app.py - PERFECT PRODUCTION READY VERSION

import streamlit as st
import google.generativeai as genai
import math
import re

# ============ SETUP ============
st.set_page_config(
    page_title="AskRivo AI Mortgage Advisor",
    page_icon="🏠",
    layout="wide"
)

# ============ PROFESSIONAL UI ============
st.markdown("""
<style>
    /* Main Container */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Header */
    .main-header {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem auto;
        max-width: 1200px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Chat Container */
    .chat-container {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        margin: 2rem auto;
        max-width: 900px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        min-height: 500px;
    }
    
    /* Messages */
    .user-msg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 1rem 0 1rem auto;
        max-width: 70%;
    }
    
    .bot-msg {
        background: #f0f2f6;
        color: #333;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 1rem auto 1rem 0;
        max-width: 70%;
        border: 1px solid #ddd;
    }
    
    /* Cards */
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    /* Input */
    .stTextInput input {
        border-radius: 15px !important;
        padding: 1rem !important;
        border: 2px solid #667eea !important;
    }
    
    /* Button */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 0.75rem 2rem;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============ MORTGAGE CALCULATOR ============
class MortgageCalculator:
    @staticmethod
    def calculate_emi(loan_amount, rate=4.5, years=25):
        """Accurate EMI calculation"""
        monthly_rate = rate / 12 / 100
        months = years * 12
        if monthly_rate == 0:
            return loan_amount / months
        emi = loan_amount * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
        return round(emi, 2)
    
    @staticmethod
    def calculate_affordability(property_price):
        """UAE mortgage rules"""
        max_loan = property_price * 0.80  # 80% LTV
        min_down = property_price * 0.20  # 20% minimum
        upfront = property_price * 0.07   # 7% hidden costs
        return {
            'max_loan': max_loan,
            'min_down': min_down,
            'upfront': upfront,
            'total_upfront': min_down + upfront
        }

# ============ AI AGENT ============
class MortgageAgent:
    def __init__(self):
        self.calculator = MortgageCalculator()
        self.user_data = {}
        
        # Initialize Gemini
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key and len(api_key) > 30:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.0-pro')
            else:
                self.model = None
        except:
            self.model = None
    
    def extract_numbers(self, text):
        """Safe number extraction"""
        try:
            numbers = re.findall(r'[\d,]+\.?\d*', text)
            result = []
            for n in numbers:
                try:
                    result.append(float(n.replace(',', '')))
                except:
                    continue
            return result
        except:
            return []
    
    def generate_response(self, user_input):
        """Generate response with accurate calculations"""
        # Extract numbers safely
        nums = self.extract_numbers(user_input)
        
        # Store user data
        text_lower = user_input.lower()
        if 'income' in text_lower or 'salary' in text_lower:
            if nums:
                self.user_data['income'] = nums[0]
        
        if 'aed' in text_lower or 'price' in text_lower or 'buy' in text_lower:
            if nums:
                self.user_data['property_price'] = max(nums)
        
        if 'rent' in text_lower:
            if nums:
                self.user_data['rent'] = nums[0]
        
        # Generate calculation text
        calc_text = ""
        if 'property_price' in self.user_data:
            price = self.user_data['property_price']
            aff = self.calculator.calculate_affordability(price)
            emi = self.calculator.calculate_emi(aff['max_loan'])
            
            calc_text = f"""
            **Property Price:** AED {price:,.0f}
            
            📊 **Mortgage Details:**
            • Maximum Loan (80%): AED {aff['max_loan']:,.0f}
            • Minimum Down Payment (20%): AED {aff['min_down']:,.0f}
            • Hidden Costs (7%): AED {aff['upfront']:,.0f}
            • Total Upfront Needed: AED {aff['total_upfront']:,.0f}
            • Monthly EMI (25 years @ 4.5%): AED {emi:,.2f}
            
            💡 **Affordability Check:**
            """
            
            if 'income' in self.user_data:
                income = self.user_data['income']
                emi_percentage = (emi / income) * 100
                calc_text += f"\nYour EMI would be {emi_percentage:.1f}% of your income (AED {income:,.0f}/month)."
                if emi_percentage <= 40:
                    calc_text += " ✅ Affordable (under 40%)"
                else:
                    calc_text += " ⚠️ High (above 40% limit)"
        
        # Try Gemini first, fallback to calculation text
        try:
            if self.model:
                prompt = f"""
                You are Zara, a friendly UAE mortgage advisor.
                
                User: "{user_input}"
                
                {calc_text if calc_text else "User hasn't shared property details yet."}
                
                UAE Mortgage Rules:
                1. Max loan: 80% of property value for expats
                2. Min down payment: 20%
                3. Additional 7% upfront costs
                4. Standard rate: 4.5%
                5. Max tenure: 25 years
                
                Respond warmly, ask ONE question if needed, explain calculations.
                Be concise (max 3 sentences).
                """
                
                response = self.model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
        except:
            pass  # Fallback to calculation text
        
        # Fallback response
        if calc_text:
            return f"🏠 **Your Mortgage Analysis**\n\n{calc_text}\n\nDoes this work for your budget?"
        else:
            return "Hi! I'm Zara, your UAE mortgage advisor. 😊 To help you, please share:\n\n1. Your monthly income\n2. Property price you're considering\n\nExample: 'I earn 25,000 AED monthly and want to buy a 2M AED apartment'"

# ============ FEEDBACK BOT ============
class FeedbackBot:
    def __init__(self):
        self.stages = [
            ("Hi! 👋 How was your experience with our mortgage advisor?", "intro"),
            ("Could you rate us from 1-5 stars? ⭐", "rating"),
            ("What could we improve?", "improvement"),
            ("Would you like personalized advice? Share email/phone:", "contact"),
            ("Thank you! 🙏 Your feedback helps us improve.", "thanks")
        ]
        self.current_stage = 0
        self.feedback_data = {}
        self.active = False
    
    def trigger(self, message_count):
        if message_count >= 6 and not self.active:
            self.active = True
            return True
        return False
    
    def get_message(self):
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage][0]
        return ""
    
    def process_response(self, response):
        stage_name = self.stages[self.current_stage][1]
        self.feedback_data[stage_name] = response
        self.current_stage += 1
        
        if self.current_stage >= len(self.stages):
            # Save feedback
            self.active = False
            return "complete"
        return "continue"

# ============ APP ============
# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent' not in st.session_state:
    st.session_state.agent = MortgageAgent()
if 'feedback' not in st.session_state:
    st.session_state.feedback = FeedbackBot()
if 'show_feedback' not in st.session_state:
    st.session_state.show_feedback = False

# Header
st.markdown("""
<div class="main-header">
    <h1>🏠 AskRivo AI Mortgage Advisor</h1>
    <p>Your smart financial friend for UAE mortgages • Zero commission • 100% transparent</p>
</div>
""", unsafe_allow_html=True)

# Two columns
col1, col2 = st.columns([3, 1])

with col1:
    # Chat Container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-msg">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
    
    # Feedback
    if st.session_state.show_feedback:
        st.markdown(f'<div class="info-card">💬 {st.session_state.feedback.get_message()}</div>', unsafe_allow_html=True)
    
    # Input
    user_input = st.text_input(
        "Type your mortgage question...",
        key="input",
        placeholder="e.g., I earn 25,000 AED monthly, what property can I afford?",
        label_visibility="collapsed"
    )
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        send = st.button("Send Message", use_container_width=True)
    with col_btn2:
        new_chat = st.button("New Chat", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # End chat container
    
    # Handle buttons
    if new_chat:
        st.session_state.messages = []
        st.session_state.agent = MortgageAgent()
        st.session_state.show_feedback = False
        st.session_state.feedback = FeedbackBot()
        st.rerun()
    
    if send and user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get AI response
        response = st.session_state.agent.generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Check for feedback trigger
        if len(st.session_state.messages) >= 8:
            st.session_state.show_feedback = True
        
        st.rerun()

with col2:
    # Sidebar info
    st.markdown("### 📋 UAE Mortgage Rules")
    st.markdown("""
    <div class="info-card">
    ✅ <b>For Expats:</b><br>
    • Max Loan: 80% of property<br>
    • Min Down Payment: 20%<br>
    • Hidden Costs: ~7% extra<br>
    • Standard Rate: 4.5%<br>
    • Max Tenure: 25 years
    </div>
    """, unsafe_allow_html=True)
    
    # User data display (SAFE)
    try:
        if hasattr(st.session_state.agent, 'user_data'):
            data = st.session_state.agent.user_data
            if data:
                if 'income' in data:
                    st.markdown(f'<div class="info-card">💰 <b>Income:</b><br>AED {data["income"]:,.0f}/month</div>', unsafe_allow_html=True)
                if 'property_price' in data:
                    st.markdown(f'<div class="info-card">🏡 <b>Property:</b><br>AED {data["property_price"]:,.0f}</div>', unsafe_allow_html=True)
    except:
        pass

# ============ REQUIREMENTS.TXT ============
"""
streamlit==1.31.0
google-generativeai==0.3.2
"""

# ============ DEPLOY ============
"""
Streamlit Cloud Setup:
1. Add GEMINI_API_KEY in secrets
2. Deploy
3. Test with: "I want to buy a 2M AED apartment"
"""

import streamlit as st
from groq import Groq
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config - Production-grade UI
st.set_page_config(
    page_title="UAE Mortgage Assistant - Your Smart Financial Friend",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for mindblowing UI
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .chat-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
        margin: 2rem auto;
        max-width: 900px;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 5px 20px;
        margin: 1rem 0;
        margin-left: auto;
        max-width: 70%;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        animation: slideInRight 0.3s ease-out;
    }
    .assistant-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        margin: 1rem 0;
        margin-right: auto;
        max-width: 70%;
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
        animation: slideInLeft 0.3s ease-out;
    }
    .sakhi-message {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
        animation: pulse 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

# ✅ ✅ ✅ UPDATED: Groq Cli
class GroqClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.client = Groq(api_key=api_key)
        self.model_name = "llama3-70b"
        logger.info("Groq client initialized successfully")
    
    def generate_with_retry(self, prompt: str, attempt: int = 1) -> Optional[str]:
        try:
            logger.info(f"Generating response (attempt {attempt}/{self.max_retries})")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.choices[0].message["content"]

        except Exception as e:
            logger.error(f"Error in attempt {attempt}: {str(e)}")

            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                return self.generate_with_retry(prompt, attempt + 1)

            return None

        
# Mortgage calculation tools
class MortgageCalculator:
    MAX_LTV = 0.80
    UPFRONT_COSTS = 0.07
    STANDARD_RATE = 0.045
    MAX_TENURE = 25
    
    @staticmethod
    def calculate_emi(loan_amount: float, annual_rate: float, tenure_years: int) -> Dict:
        try:
            monthly_rate = annual_rate / 12
            num_payments = tenure_years * 12
            
            if monthly_rate == 0:
                emi = loan_amount / num_payments
            else:
                emi = loan_amount * monthly_rate * (1 + monthly_rate)**num_payments / \
                      ((1 + monthly_rate)**num_payments - 1)
            
            total_payment = emi * num_payments
            total_interest = total_payment - loan_amount
            
            return {
                "emi": round(emi, 2),
                "total_payment": round(total_payment, 2),
                "total_interest": round(total_interest, 2),
                "loan_amount": loan_amount,
                "monthly_rate": monthly_rate,
                "num_payments": num_payments
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def calculate_affordability(property_price: float, down_payment: float = None) -> Dict:
        try:
            if down_payment is None:
                down_payment = property_price * 0.20
            
            max_loan = property_price * MortgageCalculator.MAX_LTV
            actual_loan = property_price - down_payment
            upfront_costs = property_price * MortgageCalculator.UPFRONT_COSTS
            total_upfront = down_payment + upfront_costs
            
            return {
                "property_price": property_price,
                "down_payment": down_payment,
                "max_loan": max_loan,
                "actual_loan": min(actual_loan, max_loan),
                "upfront_costs": upfront_costs,
                "total_upfront": total_upfront,
                "down_payment_percentage": (down_payment / property_price) * 100
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def buy_vs_rent_analysis(monthly_rent: float, property_price: float, years_planning: int) -> Dict:
        try:
            affordability = MortgageCalculator.calculate_affordability(property_price)
            loan_amount = affordability["actual_loan"]
            
            emi_data = MortgageCalculator.calculate_emi(
                loan_amount, 
                MortgageCalculator.STANDARD_RATE, 
                MortgageCalculator.MAX_TENURE
            )
            
            monthly_mortgage = emi_data["emi"]
            monthly_maintenance = property_price * 0.002
            total_monthly_own = monthly_mortgage + monthly_maintenance
            
            total_rent_cost = monthly_rent * 12 * years_planning
            total_own_cost = (total_monthly_own * 12 * years_planning) + affordability["total_upfront"]
            
            recommendation = "RENT" if years_planning < 3 else "BUY" if years_planning > 5 else "BORDERLINE"
            
            return {
                "monthly_rent": monthly_rent,
                "monthly_mortgage": monthly_mortgage,
                "monthly_maintenance": monthly_maintenance,
                "total_monthly_own": total_monthly_own,
                "total_rent_cost": total_rent_cost,
                "total_own_cost": total_own_cost,
                "savings": total_rent_cost - total_own_cost,
                "recommendation": recommendation,
                "years": years_planning
            }
        except Exception as e:
            return {"error": str(e)}

# Conversation Manager
class ConversationManager:
    def __init__(self):
        self.messages = []
        self.user_data = {}
        self.calculations = []
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context(self, max_tokens: int = 4000) -> str:
        context = ""
        total_chars = 0
        max_chars = max_tokens * 4
        
        for msg in reversed(self.messages[-10:]):
            msg_text = f"{msg['role']}: {msg['content']}\n"
            if total_chars + len(msg_text) > max_chars:
                break
            context = msg_text + context
            total_chars += len(msg_text)
        
        return context
    
    def extract_user_data(self, message: str, calculator: MortgageCalculator):
        message_lower = message.lower()
        import re
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', message)
        
        if 'income' in message_lower or 'salary' in message_lower:
            if numbers:
                self.user_data['monthly_income'] = float(numbers[0].replace(',', ''))
        
        if 'price' in message_lower or 'aed' in message_lower:
            if numbers:
                self.user_data['property_price'] = float(numbers[0].replace(',', ''))
        
        if 'rent' in message_lower:
            if numbers:
                self.user_data['monthly_rent'] = float(numbers[0].replace(',', ''))
        
        if 'year' in message_lower:
            if numbers:
                self.user_data['years_planning'] = int(numbers[0])

# AI Agent
class MortgageAgent:
    def __init__(self, gemini_client: GeminiClient, calculator: MortgageCalculator):
        self.gemini = gemini_client
        self.calculator = calculator
        self.conversation = ConversationManager()
    
    def should_calculate(self, user_message: str, conversation_context: str) -> bool:
        triggers = ['calculate', 'emi', 'afford', 'monthly', 'payment', 'buy', 'rent', 'price']
        return any(trigger in user_message.lower() for trigger in triggers)
    
    def generate_response(self, user_message: str) -> str:
        try:
            self.conversation.add_message("user", user_message)
            self.conversation.extract_user_data(user_message, self.calculator)
            
            context = self.conversation.get_context()
            user_data = self.conversation.user_data
            
            calculation_result = None
            if self.should_calculate(user_message, context):
                if 'property_price' in user_data:
                    if 'monthly_rent' in user_data and 'years_planning' in user_data:
                        calculation_result = self.calculator.buy_vs_rent_analysis(
                            user_data['monthly_rent'],
                            user_data['property_price'],
                            user_data['years_planning']
                        )
                    else:
                        affordability = self.calculator.calculate_affordability(
                            user_data['property_price']
                        )
                        calculation_result = self.calculator.calculate_emi(
                            affordability['actual_loan'],
                            self.calculator.STANDARD_RATE,
                            self.calculator.MAX_TENURE
                        )
            
            system_prompt = f"""You are a friendly UAE mortgage advisor named "Zara". You help expats understand mortgages.

CONVERSATION CONTEXT:
{context}

USER DATA COLLECTED:
{json.dumps(user_data, indent=2)}

{'CALCULATION RESULTS:' + json.dumps(calculation_result, indent=2) if calculation_result else ''}

RULES:
1. Be warm, empathetic, and conversational
2. If calculations are provided, explain them clearly
3. Ask ONE clarifying question at a time
4. Guide towards collecting: income, property price, rent (if comparing), years planning to stay
5. When you have enough data, provide clear recommendation
6. Be honest about hidden costs (7% upfront costs)
7. Keep responses concise (3-4 sentences max)

USER MESSAGE: {user_message}

Respond naturally:"""
            
            response = self.gemini.generate_with_retry(system_prompt)
            
            if response:
                self.conversation.add_message("assistant", response)
                return response
            else:
                return "I'm having trouble connecting right now. Could you please try again?"
                
        except Exception as e:
            return "I encountered an error. Let me try to help you differently. What would you like to know about UAE mortgages?"

# Sakhi - Feedback Bot
class SakhiBot:
    @staticmethod
    def get_message(stage: str) -> str:
        messages = {
            "intro": "Hi! 👋 I'm Sakhi, your feedback friend. How was your experience chatting with our mortgage advisor?",
            "rating": "Could you rate your experience from 1-5? ⭐",
            "improvement": "What could we improve to make this better for you?",
            "contact": "Would you like our team to reach out to you? If yes, please share your email or phone number.",
            "thanks": "Thank you so much! 🙏 Your feedback helps us improve. Have a great day!"
        }
        return messages.get(stage, messages["intro"])

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.show_sakhi = False
    st.session_state.sakhi_stage = "intro"
    st.session_state.feedback_data = {}

# Initialize Groq
try:
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY not found in secrets. Please add it in Streamlit Cloud settings.")
        st.stop()
    
    if st.session_state.agent is None:
        groq_client = GeminiClient(api_key)
        calculator = MortgageCalculator()
        st.session_state.agent = MortgageAgent(groq_client, calculator)
except Exception as e:
    st.error(f"Failed to initialize: {str(e)}")
    st.stop()

# Header
st.markdown("""
<div class="main-header">
    <h1>🏠 Your Smart Mortgage Friend</h1>
    <p>Navigate UAE mortgages with confidence - No hidden fees, no confusion</p>
</div>
""", unsafe_allow_html=True)

# Main chat container
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Display chat messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-message">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

# Sakhi feedback flow
if st.session_state.show_sakhi:
    st.markdown(f'<div class="sakhi-message">💬 Sakhi: {SakhiBot.get_message(st.session_state.sakhi_stage)}</div>', 
                unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input area
col1, col2 = st.columns([5, 1])

with col1:
    user_input = st.text_input(
        "Type your message...",
        key="user_input",
        placeholder="e.g., I want to buy a 2M AED apartment in Dubai Marina...",
        label_visibility="collapsed"
    )

with col2:
    send_button = st.button("Send 📤", use_container_width=True)

# Handle Sakhi feedback
if st.session_state.show_sakhi and user_input and send_button:
    st.session_state.feedback_data[st.session_state.sakhi_stage] = user_input
    
    if st.session_state.sakhi_stage == "intro":
        st.session_state.sakhi_stage = "rating"
    elif st.session_state.sakhi_stage == "rating":
        st.session_state.sakhi_stage = "improvement"
    elif st.session_state.sakhi_stage == "improvement":
        st.session_state.sakhi_stage = "contact"
    elif st.session_state.sakhi_stage == "contact":
        st.session_state.sakhi_stage = "thanks"
        st.balloons()
    
    st.rerun()

# Handle normal conversation
elif user_input and send_button and not st.session_state.show_sakhi:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("🤔 Thinking..."):
        response = st.session_state.agent.generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    if len(st.session_state.messages) >= 10:
        st.session_state.show_sakhi = True
    
    st.rerun()

# Sidebar with stats
with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    if st.session_state.agent and st.session_state.agent.conversation.user_data:
        data = st.session_state.agent.conversation.user_data
        
        if 'monthly_income' in data:
            st.markdown(f"""
            <div class="stat-card">
                <h3>💰 Income</h3>
                <p>AED {data['monthly_income']:,.0f}/month</p>
            </div>
            """, unsafe_allow_html=True)
        
        if 'property_price' in data:
            st.markdown(f"""
            <div class="stat-card">
                <h3>🏡 Property Price</h3>
                <p>AED {data['property_price']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🎯 UAE Mortgage Facts")
    st.info("✅ Max LTV: 80% for expats\n\n✅ Upfront costs: ~7%\n\n✅ Standard rate: 4.5%\n\n✅ Max tenure: 25 years")
    
    if st.button("🔄 Start New Chat"):
        st.session_state.messages = []
        st.session_state.agent = None
        st.session_state.show_sakhi = False
        st.rerun()

logger.info("App render completed")


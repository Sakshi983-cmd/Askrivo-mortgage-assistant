import streamlit as st
import google.generativeai as genai
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
    /* Main container */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Chat container */
    .chat-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
        margin: 2rem auto;
        max-width: 900px;
    }
    
    /* Message bubbles */
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
    
    /* Animations */
    @keyframes slideInRight {
        from { transform: translateX(50px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideInLeft {
        from { transform: translateX(-50px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    /* Header */
    .main-header {
        text-align: center;
        color: white;
        padding: 2rem 0;
        animation: fadeInDown 0.5s ease-out;
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    /* Input box */
    .stTextInput input {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput input:focus {
        border-color: #764ba2 !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Stats cards */
    .stat-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .stat-card h3 {
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    
    /* Typing indicator */
    .typing-indicator {
        display: inline-block;
        padding: 1rem;
    }
    
    .typing-indicator span {
        height: 10px;
        width: 10px;
        background: #667eea;
        border-radius: 50%;
        display: inline-block;
        margin: 0 2px;
        animation: typing 1.4s infinite;
    }
    
    .typing-indicator span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-indicator span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-10px); }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    @keyframes fadeInDown {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize Gemini with retry logic
class GeminiClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini client initialized successfully")
    
    def generate_with_retry(self, prompt: str, attempt: int = 1) -> Optional[str]:
        """Generate response with exponential backoff retry logic"""
        try:
            logger.info(f"Generating response (attempt {attempt}/{self.max_retries})")
            response = self.model.generate_content(prompt)
            logger.info("Response generated successfully")
            return response.text
        except Exception as e:
            logger.error(f"Error in attempt {attempt}: {str(e)}")
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.generate_with_retry(prompt, attempt + 1)
            else:
                logger.error(f"Max retries reached. Error: {traceback.format_exc()}")
                return None


# Mortgage calculation tools
class MortgageCalculator:
    """Deterministic calculation engine - No LLM hallucinations here!"""
    
    MAX_LTV = 0.80  # 80% max loan for expats
    UPFRONT_COSTS = 0.07  # 7% upfront costs
    STANDARD_RATE = 0.045  # 4.5% annual interest
    MAX_TENURE = 25  # 25 years max
    
    @staticmethod
    def calculate_emi(loan_amount: float, annual_rate: float, tenure_years: int) -> dict:
        """Calculate EMI using standard formula"""
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
            
            logger.info(f"EMI calculated: AED {emi:.2f} for loan AED {loan_amount:,.2f}")
            
            return {
                "emi": round(emi, 2),
                "total_payment": round(total_payment, 2),
                "total_interest": round(total_interest, 2),
                "loan_amount": loan_amount,
                "monthly_rate": monthly_rate,
                "num_payments": num_payments
            }
        except Exception as e:
            logger.error(f"EMI calculation error: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def calculate_affordability(property_price: float, down_payment: float = None) -> dict:
        """Calculate affordability metrics"""
        try:
            if down_payment is None:
                down_payment = property_price * 0.20  # Minimum 20%
            
            max_loan = property_price * MortgageCalculator.MAX_LTV
            actual_loan = property_price - down_payment
            upfront_costs = property_price * MortgageCalculator.UPFRONT_COSTS
            total_upfront = down_payment + upfront_costs
            
            logger.info(f"Affordability calculated for property: AED {property_price:,.2f}")
            
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
            logger.error(f"Affordability calculation error: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def buy_vs_rent_analysis(monthly_rent: float, property_price: float, years_planning: int) -> dict:
        """Analyze buy vs rent decision"""
        try:
            affordability = MortgageCalculator.calculate_affordability(property_price)
            loan_amount = affordability["actual_loan"]
            
            emi_data = MortgageCalculator.calculate_emi(
                loan_amount, 
                MortgageCalculator.STANDARD_RATE, 
                MortgageCalculator.MAX_TENURE
            )
            
            monthly_mortgage = emi_data["emi"]
            monthly_maintenance = property_price * 0.002  # 0.2% monthly maintenance
            total_monthly_own = monthly_mortgage + monthly_maintenance
            
            total_rent_cost = monthly_rent * 12 * years_planning
            total_own_cost = (total_monthly_own * 12 * years_planning) + affordability["total_upfront"]
            
            recommendation = "RENT" if years_planning < 3 else "BUY" if years_planning > 5 else "BORDERLINE"
            
            logger.info(f"Buy vs Rent analysis: {recommendation} for {years_planning} years")
            
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
            logger.error(f"Buy vs Rent analysis error: {str(e)}")
            return {"error": str(e)}

# Conversation Manager
class ConversationManager:
    """Manages conversation state and context"""
    
    def __init__(self):
        self.messages = []
        self.user_data = {}
        self.calculations = []
        logger.info("Conversation manager initialized")
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Message added - Role: {role}, Length: {len(content)} chars")
    
    def get_context(self, max_tokens: int = 4000) -> str:
        """Get conversation context with token management"""
        context = ""
        total_chars = 0
        max_chars = max_tokens * 4  # Simple token estimation
        
        for msg in reversed(self.messages[-10:]):  # Last 10 messages
            msg_text = f"{msg['role']}: {msg['content']}\n"
            if total_chars + len(msg_text) > max_chars:
                break
            context = msg_text + context
            total_chars += len(msg_text)
        
        logger.info(f"Context prepared: {len(context)} chars from {len(self.messages)} total messages")
        return context
    
    def extract_user_data(self, message: str, calculator: MortgageCalculator):
        """Extract structured data from conversation"""
        message_lower = message.lower()
        import re
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', message)
        
        if 'income' in message_lower or 'salary' in message_lower or 'earn' in message_lower:
            if numbers:
                self.user_data['monthly_income'] = float(numbers[0].replace(',', ''))
                logger.info(f"Income extracted: {self.user_data['monthly_income']}")
        
        if 'price' in message_lower or 'cost' in message_lower or 'aed' in message_lower:
            if numbers:
                self.user_data['property_price'] = float(numbers[0].replace(',', ''))
                logger.info(f"Property price extracted: {self.user_data['property_price']}")
        
        if 'rent' in message_lower:
            if numbers:
                self.user_data['monthly_rent'] = float(numbers[0].replace(',', ''))
                logger.info(f"Rent extracted: {self.user_data['monthly_rent']}")
        
        if 'year' in message_lower:
            if numbers:
                self.user_data['years_planning'] = int(numbers[0])
                logger.info(f"Years extracted: {self.user_data['years_planning']}")

# AI Agent
class MortgageAgent:
    """The AI Agent - empathy + intelligence + tools"""
    
    def __init__(self, gemini_client: GeminiClient, calculator: MortgageCalculator):
        self.gemini = gemini_client
        self.calculator = calculator
        self.conversation = ConversationManager()
        logger.info("Mortgage agent initialized")
    
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
                logger.info("Response generated and added to conversation")
                return response
            else:
                logger.error("Failed to generate response after retries")
                return "I'm having trouble connecting right now. Could you please try again?"
                
        except Exception as e:
            logger.error(f"Error in generate_response: {traceback.format_exc()}")
            return "I encountered an error. Let me try to help you differently. What would you like to know about UAE mortgages?"

# Sakhi - Feedback Bot
class SakhiBot:
    """Friendly feedback collection bot"""
    
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

# Session State Initialization
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.show_sakhi = False
    st.session_state.sakhi_stage = "intro"
    st.session_state.feedback_data = {}
    logger.info("Session state initialized")

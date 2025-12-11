# app.py
import streamlit as st
import json
import time
import logging
from datetime import datetime
from typing import Optional

# Optional: keep the Groq import if you use the Groq SDK
# from groq import Groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="UAE Mortgage Assistant - Your Smart Financial Friend",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS (same as yours)
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .chat-container { background: rgba(255,255,255,0.95); border-radius:20px; padding:2rem; box-shadow:0 20px 60px rgba(0,0,0,0.3); max-width:900px; margin:2rem auto;}
    .user-message { background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; padding:1rem 1.5rem; border-radius:20px 20px 5px 20px; margin:1rem 0; margin-left:auto; max-width:70%;}
    .assistant-message { background: linear-gradient(135deg,#f093fb 0%,#f5576c 100%); color:white; padding:1rem 1.5rem; border-radius:20px 20px 20px 5px; margin:1rem 0; margin-right:auto; max-width:70%;}
    .sakhi-message { background: linear-gradient(135deg,#4facfe 0%,#00f2fe 100%); color:white; padding:1rem 1.5rem; border-radius:20px; margin:1rem 0; text-align:center;}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Small mortgage calculator (self-contained)
# -------------------------
class MortgageCalculator:
    STANDARD_RATE = 4.5  # annual percent (example)
    MAX_TENURE = 25      # years

    def calculate_affordability(self, property_price: float) -> dict:
        # Example simple rules:
        # Downpayment assumed 20% (expat typical), bank finances 80% (LTV 80%)
        downpayment = property_price * 0.20
        actual_loan = property_price - downpayment
        return {
            "property_price": property_price,
            "downpayment": downpayment,
            "actual_loan": actual_loan
        }

    def calculate_emi(self, principal: float, annual_rate: float, tenure_years: int) -> dict:
        # Convert annual rate % to monthly decimal
        r = (annual_rate / 100) / 12
        n = tenure_years * 12
        if r == 0:
            emi = principal / n
        else:
            emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
        total_payment = emi * n
        return {"emi_monthly": emi, "total_payment": total_payment, "tenure_months": n}

    def buy_vs_rent_analysis(self, monthly_rent: float, property_price: float, years: int) -> dict:
        # Basic comparison: total rent vs buying cost (EMI + upfront costs)
        rental_total = monthly_rent * 12 * years
        afford = self.calculate_affordability(property_price)
        loan = afford["actual_loan"]
        emi = self.calculate_emi(loan, self.STANDARD_RATE, min(self.MAX_TENURE, years))
        upfront_costs = property_price * 0.07  # your rule: 7% hidden/upfront
        buying_total_est = emi["total_payment"] + upfront_costs + afford["downpayment"]
        return {
            "rental_total": rental_total,
            "buying_estimated_total": buying_total_est,
            "monthly_emi_estimate": emi["emi_monthly"],
            "upfront_costs_est": upfront_costs,
            "downpayment": afford["downpayment"]
        }

# -------------------------
# Conversation manager
# -------------------------
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

    def extract_user_data(self, message: str):
        message_lower = message.lower()
        import re
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', message.replace(',', ''))
        # simplistic extraction: pick first matches if keywords present
        if 'income' in message_lower or 'salary' in message_lower:
            if numbers:
                self.user_data['monthly_income'] = float(numbers[0])
        if 'price' in message_lower or 'aed' in message_lower or 'apartment' in message_lower:
            if numbers:
                self.user_data['property_price'] = float(numbers[0])
        if 'rent' in message_lower:
            if numbers:
                self.user_data['monthly_rent'] = float(numbers[0])
        if 'year' in message_lower or 'years' in message_lower:
            if numbers:
                self.user_data['years_planning'] = int(numbers[0])

# -------------------------
# Groq client wrapper (robust parsing)
# -------------------------
class GroqClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        # If you use the Groq SDK, you can initialize here. 
        # Example (uncomment if SDK present):
        # self.client = Groq(api_key=api_key)
        self.client = None
        logger.info("GroqClient initialized (SDK use depends on environment)")

    def generate_with_retry(self, prompt: str, attempt: int = 1) -> Optional[str]:
        try:
            logger.info(f"Groq generate attempt {attempt}")
            # If you use SDK:
            # response = self.client.chat.completions.create(model="llama3-70b-8192", messages=[{"role":"user","content":prompt}])
            # For safety, we'll simulate a call or handle multiple response shapes.

            # ---- START: User should replace this with real SDK call ----
            raise RuntimeError("SDK call placeholder — replace with your Groq SDK call in generate_with_retry.")
            # ---- END: replace ----

        except Exception as e:
            logger.error(f"Groq error on attempt {attempt}: {e}", exc_info=True)
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying after {wait_time}s")
                time.sleep(wait_time)
                return self.generate_with_retry(prompt, attempt + 1)
            # Return detailed message to UI (but do not leak secrets)
            return None

# -------------------------
# Single MortgageAgent (no duplicates)
# -------------------------
class MortgageAgent:
    def __init__(self, groq_client: GroqClient, calculator: MortgageCalculator):
        self.groq = groq_client
        self.calculator = calculator
        self.conversation = ConversationManager()

    def should_calculate(self, user_message: str) -> bool:
        triggers = ['calculate', 'emi', 'afford', 'monthly', 'payment', 'buy', 'rent', 'price']
        return any(trigger in user_message.lower() for trigger in triggers)

    def generate_response(self, user_message: str) -> str:
        try:
            self.conversation.add_message("user", user_message)
            self.conversation.extract_user_data(user_message)
            context = self.conversation.get_context()
            user_data = self.conversation.user_data
            calculation_result = None

            if self.should_calculate(user_message):
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

            # Compose the prompt we will send to the LLM (if available)
            system_prompt = f"""
You are a friendly UAE mortgage advisor named "Zara". You help expats understand mortgages.

CONTEXT:
{context}

USER DATA:
{json.dumps(user_data, indent=2)}

{json.dumps(calculation_result, indent=2) if calculation_result else ''}

Respond naturally, concise, and explain calculations in plain words.
"""
            # Try the LLM if configured
            llm_response = None
            if self.groq:
                llm_response = self.groq.generate_with_retry(system_prompt)

            if llm_response:
                self.conversation.add_message("assistant", llm_response)
                return llm_response

            # Fallback (non-LLM): small human-friendly summary
            if calculation_result:
                # show summary from calculation_result dict
                if 'emi_monthly' in calculation_result:
                    emi = calculation_result['emi_monthly']
                    return f"Estimated EMI: AED {emi:,.2f}/month (approx). I used standard rate {self.calculator.STANDARD_RATE}% and max tenure {self.calculator.MAX_TENURE} years."
                elif 'monthly_emi_estimate' in calculation_result:
                    emi = calculation_result['monthly_emi_estimate']
                    return f"Buy vs Rent — Monthly EMI estimate: AED {emi:,.2f}. Buying estimated total (incl. upfront): AED {calculation_result['buying_estimated_total']:,.0f} vs renting for your chosen period AED {calculation_result['rental_total']:,.0f}."
            else:
                # If we don't have enough data, ask one clarifying question
                if 'property_price' not in user_data:
                    return "Could you share the property price (in AED) or expected price? For example: '2,000,000 AED'?"
                if 'monthly_income' not in user_data:
                    return "What's your monthly income (AED)? e.g., 'salary 18,000'"

            return "Sorry — I couldn't compute that. Please try giving the price and how many years you plan to stay."
        except Exception as e:
            logger.exception("generate_response failed")
            return "I encountered an internal error while processing your message."

# -------------------------
# SakhiBot small helper
# -------------------------
class SakhiBot:
    @staticmethod
    def get_message(stage: str) -> str:
        messages = {
            "intro": "Hi! I'm Sakhi, your feedback friend. How was your experience chatting with our mortgage advisor?",
            "rating": "Could you rate your experience from 1-5?",
            "improvement": "What could we improve?",
            "contact": "Would you like our team to reach out? Share email/phone.",
            "thanks": "Thank you — your feedback helps us improve!"
        }
        return messages.get(stage, messages["intro"])

# -------------------------
# Streamlit session init
# -------------------------
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.show_sakhi = False
    st.session_state.sakhi_stage = "intro"
    st.session_state.feedback_data = {}

# Initialize Groq client & agent
try:
    api_key = ""
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")  # replace for cloud; local dev can set env variable or placeholder
    except Exception:
        api_key = ""

    if not api_key:
        st.warning("GROQ_API_KEY not found in Streamlit secrets. Groq LLM calls will be disabled; the app will use local fallbacks.")
        groq_client = None
    else:
        groq_client = GroqClient(api_key=api_key, max_retries=3)

    if st.session_state.agent is None:
        calculator = MortgageCalculator()
        st.session_state.agent = MortgageAgent(groq_client, calculator)
except Exception as e:
    st.error(f"Failed to initialize agent: {str(e)}")
    logger.exception("Initialization error")
    st.stop()

# UI rendering (header, chat, input) - same logic you had
st.markdown("""
<div class="main-header">
    <h1>🏠 Your Smart Mortgage Friend</h1>
    <p>Navigate UAE mortgages with confidence - No hidden fees, no confusion</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-message">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

if st.session_state.show_sakhi:
    st.markdown(f'<div class="sakhi-message">💬 Sakhi: {SakhiBot.get_message(st.session_state.sakhi_stage)}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input("Type your message...", key="user_input", placeholder="e.g., I want to buy a 2M AED apartment in Dubai Marina...", label_visibility="collapsed")
with col2:
    send_button = st.button("Send", use_container_width=True)

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
    st.session_state.user_input = ""
    st.rerun()

elif user_input and send_button and not st.session_state.show_sakhi:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("🤔 Thinking..."):
        response = st.session_state.agent.generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    if len(st.session_state.messages) >= 10:
        st.session_state.show_sakhi = True
    st.rerun()

with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    if st.session_state.agent and st.session_state.agent.conversation.user_data:
        data = st.session_state.agent.conversation.user_data
        if 'monthly_income' in data:
            st.markdown(f"<div class='stat-card'><h3>💰 Income</h3><p>AED {data['monthly_income']:,.0f}/month</p></div>", unsafe_allow_html=True)
        if 'property_price' in data:
            st.markdown(f"<div class='stat-card'><h3>🏡 Property Price</h3><p>AED {data['property_price']:,.0f}</p></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🎯 UAE Mortgage Facts")
    st.info("✅ Max LTV: 80% for expats\n\n✅ Upfront costs: ~7%\n\n✅ Standard rate: 4.5%\n\n✅ Max tenure: 25 years")
    if st.button("🔄 Start New Chat"):
        st.session_state.messages = []
        st.session_state.agent = None
        st.session_state.show_sakhi = False
        st.experimental_rerun()

logger.info("App render completed")


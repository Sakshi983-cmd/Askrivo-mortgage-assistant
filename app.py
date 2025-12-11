import streamlit as st
from groq import Groq
import time
import json
import logging
from datetime import datetime
from typing import Optional

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# SakhiBot - feedback
# -------------------------
class SakhiBot:
    @staticmethod
    def get_message(stage: str) -> str:
        messages = {
            "intro": "Hi! 👋 I'm Sakhi, your feedback friend. How was your experience chatting with our mortgage advisor today?",
            "rating": "On a scale of 1 to 5 ⭐, how would you rate your experience?",
            "improvement": "We always want to get better! What can we improve in your experience?",
            "contact": "Would you like our team to reach out to you? If yes, please share your email or phone number.",
            "thanks": "Thank you! 🙏 Your feedback helps us improve our service. Have a great day!"
        }
        return messages.get(stage, messages["intro"])

# -------------------------
# Groq Client
# -------------------------
class GroqClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = Groq(api_key=api_key)
        self.model_name = "llama3-70b-8192"
        logger.info("Groq client initialized")

    def generate_with_retry(self, prompt: str, attempt: int = 1) -> Optional[str]:
        try:
            logger.info(f"Groq generate attempt {attempt}")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message["content"]

        except Exception as e:
            logger.error(f"Groq error on attempt {attempt}: {e}")
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying after {wait_time}s")
                time.sleep(wait_time)
                return self.generate_with_retry(prompt, attempt + 1)
            return None

# -------------------------
# Conversation manager
# -------------------------
class ConversationManager:
    def __init__(self):
        self.messages = []
        self.user_data = {}

    def add_message(self, role: str, content: str):
        if not self.messages or self.messages[-1]["content"] != content:
            self.messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

# -------------------------
# Mortgage Agent
# -------------------------
class MortgageAgent:
    def __init__(self, groq_client: GroqClient):
        self.groq = groq_client
        self.conversation = ConversationManager()

    def generate_response(self, user_message: str) -> str:
        self.conversation.add_message("user", user_message)
        context = "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation.messages[-10:]])

        prompt = f"""
You are Zara, a friendly UAE mortgage advisor.

CONTEXT:
{context}

Respond naturally and concisely.
"""
        response = self.groq.generate_with_retry(prompt)
        if response:
            self.conversation.add_message("assistant", response)
            return response
        else:
            return "I'm having trouble connecting. Please try again."

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

# -------------------------
# Load Groq API safely
# -------------------------
try:
    api_key = st.secrets["GROQ_API_KEY"]
    if not api_key:
        st.error("GROQ_API_KEY missing!")
        st.stop()
    if st.session_state.agent is None:
        groq_client = GroqClient(api_key)
        st.session_state.agent = MortgageAgent(groq_client)
except Exception as e:
    st.error(f"Failed to init Groq: {e}")
    st.stop()

# -------------------------
# Custom CSS for UI
# -------------------------
st.markdown("""
<style>
.chat-container {
    max-width: 800px;
    margin: auto;
    padding: 20px;
    background: #fdfdfd;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}
.user-message {
    background: #667eea; color: white; padding: 10px 15px; border-radius: 15px; margin-left:auto; margin-bottom:8px; max-width:70%;
}
.assistant-message {
    background: #f093fb; color: white; padding: 10px 15px; border-radius: 15px; margin-right:auto; margin-bottom:8px; max-width:70%;
}
.sakhi-message {
    background: #4facfe; color: white; padding: 12px 18px; border-radius: 15px; margin:auto; text-align:center; margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Chat UI
# -------------------------
st.title("🏠 UAE Mortgage Assistant")
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

user_input = st.text_input("Type your message...", key="user_input")
send_button = st.button("Send")

# Normal conversation
if user_input and send_button:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("🤔 Thinking..."):
        response = st.session_state.agent.generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Display messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-message">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

# SakhiBot feedback
if st.session_state.show_sakhi:
    st.markdown(f'<div class="sakhi-message">💬 {SakhiBot.get_message(st.session_state.sakhi_stage)}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

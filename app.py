import streamlit as st
import time
import logging
from groq import Groq

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="AskRivo — UAE Mortgage Advisor", layout="wide")

# -------------------------
# Logger
# -------------------------
logger = logging.getLogger(__name__)

# -------------------------
# Load API key from Streamlit Secrets
# -------------------------
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY missing! Add it in Streamlit Secrets.")
    st.stop()

# -------------------------
# Initialize Groq client
# -------------------------
client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama3-70b-8192"

# -------------------------
# Helper: Generate response with retry
# -------------------------
def get_llm_response(user_message, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Groq attempt {attempt}")
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are AskRivo, a helpful UAE mortgage assistant."},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2
            )
            try:
                return response.choices[0].message["content"]
            except Exception:
                return getattr(response.choices[0], "text", str(response))
        except Exception as e:
            logger.error(f"Groq error on attempt {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            return "Sorry — I can't reach my language service right now. I can still show calculations."

# -------------------------
# UI
# -------------------------
st.title("AskRivo — UAE Mortgage Advisor")
st.write("Conversational Buy vs Rent guidance — accurate math, friendly advice.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat input
user_input = st.text_input("Ask anything about buying, renting, or mortgage:")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    reply = get_llm_response(user_input)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**AskRivo:** {msg['content']}")


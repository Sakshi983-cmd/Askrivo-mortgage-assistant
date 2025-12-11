import streamlit as st
import json
import logging
from utils.groq_client import GroqClient
from utils.mortgage_calculator import buy_vs_rent, calculate_emi, affordability
from utils.conversation import ConversationManager
from utils.sakhi_bot import SakhiBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="AskRivo - UAE Mortgage Assistant", page_icon="🏠", layout="wide")

# CSS minimal to reduce white gaps
st.markdown("""
<style>
body { background: #f6f7fb; }
.chat-container { max-width: 900px; margin: 20px auto; background: #ffffff; padding: 18px; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.06); }
.user-message { background:#667eea; color:white; padding:10px 14px; border-radius:12px; margin-left:auto; max-width:70%; margin-bottom:8px;}
.assistant-message { background:#f093fb; color:white; padding:10px 14px; border-radius:12px; margin-right:auto; max-width:70%; margin-bottom:8px;}
.sakhi-message { background:#4facfe; color:white; padding:12px; border-radius:10px; text-align:center; margin: 8px 0;}
</style>
""", unsafe_allow_html=True)

# Session init
if 'conv' not in st.session_state:
    st.session_state.conv = ConversationManager()
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'show_sakhi' not in st.session_state:
    st.session_state.show_sakhi = False
if 'sakhi_stage' not in st.session_state:
    st.session_state.sakhi_stage = "intro"
if 'groq' not in st.session_state:
    st.session_state.groq = None

# Load Groq API key from Streamlit Secrets
api_key = st.secrets.get("GROQ_API_KEY", "")
if not api_key:
    st.error("GROQ_API_KEY missing. Set it in Streamlit Cloud Secrets.")
    st.stop()

# Init Groq client only once
if st.session_state.groq is None:
    st.session_state.groq = GroqClient(api_key)

# Header
st.markdown("<h1>AskRivo — UAE Mortgage Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p>Conversational Buy vs Rent guidance — accurate math, friendly advice.</p>", unsafe_allow_html=True)

# Input area
col1, col2 = st.columns([4,1])
with col1:
    user_text = st.text_input("Ask anything about buying, renting, or mortgage. Example: \"I want to buy a 2,000,000 AED apartment; I pay 8,000 AED rent; I will stay 5 years.\"")
with col2:
    send = st.button("Send")

# When user sends
if send and user_text:
    # save user message to conversation and messages
    st.session_state.conv.add_message("user", user_text)
    st.session_state.messages.append({"role":"user","content":user_text})

    # extract data
    user_data = st.session_state.conv.extract_user_data(user_text)

    # If property_price detected and the user intent indicates buy/rent comparison, compute
    if 'property_price' in user_data:
        prop = user_data.get("property_price")
        rent = user_data.get("monthly_rent")
        years = user_data.get("years_planning", 5)
        calc = buy_vs_rent(prop, rent, years)
        # deterministic facts to include in LLM prompt
        facts = {
            "property_price": prop,
            "loan_amount": calc["reasoning"]["loan_amount"],
            "downpayment": calc["reasoning"]["downpayment"],
            "upfront_costs": calc["reasoning"]["upfront_costs"],
            "emi_monthly": calc["reasoning"]["emi_monthly"],
            "recommendation": calc["recommendation"],
            "years_planning": years,
            "monthly_rent": rent
        }
        prompt = (
            "You are Zara, a friendly UAE mortgage advisor. "
            "Do not compute math — the numbers below are computed already. Use them to explain the recommendation in 2-3 sentences.\n\n"
            f"FACTS:\n{json.dumps(facts, indent=2)}\n\n"
            "Explain the recommendation and mention hidden costs (7%) and 80% LTV rule. Be concise and empathetic."
        )
        # call LLM
        assistant_text = st.session_state.groq.generate_with_retry(prompt)
        # add assistant message
        st.session_state.conv.add_message("assistant", assistant_text)
        st.session_state.messages.append({"role":"assistant","content":assistant_text})
    else:
        # no property price — ask gently for required info
        assistant_text = "Could you share the property price (in AED) and (optionally) current monthly rent and how many years you plan to stay? e.g., '2,000,000 AED, rent 8,000, stay 5 years.'"
        st.session_state.conv.add_message("assistant", assistant_text)
        st.session_state.messages.append({"role":"assistant","content":assistant_text})

    # Show Sakhi after several exchanges
    if len(st.session_state.messages) >= 8:
        st.session_state.show_sakhi = True

# Chat display
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f'<div class="user-message">👤 {m["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 {m["content"]}</div>', unsafe_allow_html=True)

if st.session_state.show_sakhi:
    st.markdown(f'<div class="sakhi-message">💬 {SakhiBot.get_message(st.session_state.sakhi_stage)}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar stats and controls
with st.sidebar:
    st.header("Quick Stats")
    ud = st.session_state.conv.user_data
    if ud:
        if "monthly_income" in ud:
            st.write("Monthly income: AED {:,.0f}".format(ud["monthly_income"]))
        if "property_price" in ud:
            st.write("Property price: AED {:,.0f}".format(ud["property_price"]))
        if "monthly_rent" in ud:
            st.write("Current rent: AED {:,.0f}".format(ud["monthly_rent"]))
        if "years_planning" in ud:
            st.write("Years planning: {}".format(ud["years_planning"]))
    st.markdown("---")
    st.info("Max LTV: 80% • Upfront ~7% • Standard rate: 4.5% • Max tenure: 25 years")
    st.markdown("---")
    if st.button("Start New Chat"):
        st.session_state.messages = []
        st.session_state.conv = ConversationManager()
        st.session_state.show_sakhi = False
        st.session_state.sakhi_stage = "intro"
        st.experimental_rerun()


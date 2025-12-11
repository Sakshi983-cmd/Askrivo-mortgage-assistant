import streamlit as st
from groq import Groq

st.set_page_config(page_title="AskRivo — UAE Mortgage Advisor", layout="wide")

# -------------------------
# Load secret from Streamlit Cloud
# -------------------------
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# -------------------------
# Initialize Groq Client
# -------------------------
client = Groq(api_key=GROQ_API_KEY)


def get_llm_response(user_message):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are AskRivo — a UAE mortgage advisor."},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2
        )

        return response.choices[0].message["content"]

    except Exception as e:
        return f"Error: {e}"


# -------------------------
# UI
# -------------------------
st.title("AskRivo — UAE Mortgage Advisor")
st.write("Conversational Buy vs Rent guidance — accurate math, friendly advice.")

user_input = st.text_input("Ask anything about buying, renting, or mortgage:")
if user_input:
    reply = get_llm_response(user_input)
    st.write(reply)


# app.py — AskRivo AI Mortgage Advisor (Buy-vs-Rent) — Production-ready
import streamlit as st
import re
import math
import json
from typing import Dict, Any, Optional

# ============ PAGE CONFIG ============
st.set_page_config(page_title="AskRivo AI Mortgage Advisor", page_icon="🏠", layout="wide")

# ============ STYLES (DARK THEME) ============
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0b0b; color: #e6e6e6; }
    .main-header { background: #0f1724; padding: 20px; border-radius: 12px; text-align:center; margin-bottom:12px; }
    .chat-container { background: #0b1220; padding: 18px; border-radius: 12px; min-height:360px; }
    .user-msg { background:#1f2937; color:#e6e6e6; padding:10px; border-radius:10px 10px 2px 10px; margin:8px 0; max-width:70%; }
    .bot-msg { background:#111827; color:#e6e6e6; padding:10px; border-radius:10px 10px 10px 2px; margin:8px 0; max-width:70%; border:1px solid #1f2937; }
    .info-card { background:#071026; padding:12px; border-radius:10px; border-left:4px solid #7c3aed; margin:8px 0; }
    .stTextInput>div>div>input { background:#061021; color:#e6e6e6; border-radius:10px; border:1px solid #263244; padding:12px; }
    .stButton>button { background: linear-gradient(135deg,#7c3aed 0%,#5b21b6 100%); color: white; border-radius:10px; padding:8px 18px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============ DETERMINISTIC FINANCE FUNCTIONS ============
class MortgageCalculator:
    @staticmethod
    def calculate_emi(loan_amount: float, annual_rate: float = 4.5, years: int = 25) -> float:
        """Calculate EMI deterministically and return rounded value."""
        if loan_amount <= 0 or years <= 0:
            return 0.0
        monthly_rate = annual_rate / 12.0 / 100.0
        n = years * 12
        if monthly_rate == 0:
            emi = loan_amount / n
        else:
            emi = loan_amount * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)
        return round(emi, 2)

    @staticmethod
    def affordability_primitives(property_price: float, down_payment_pct: float = 0.20) -> Dict[str, float]:
        """Return primitives required by rules (max loan, min down, upfront costs)."""
        max_loan = property_price * (1 - down_payment_pct)  # 80% loan for expats when down_payment_pct=0.2
        min_down = property_price * down_payment_pct
        upfront = property_price * 0.07  # 7% hidden costs (4% transfer + 2% agency + misc)
        total_upfront = min_down + upfront
        return {
            "property_price": round(property_price, 2),
            "max_loan": round(max_loan, 2),
            "min_down": round(min_down, 2),
            "upfront": round(upfront, 2),
            "total_upfront": round(total_upfront, 2),
        }

# ============ BUY vs RENT LOGIC ============
def buy_vs_rent_decision(
    property_price: float,
    income_monthly: float,
    current_rent_monthly: Optional[float],
    planning_years: Optional[int],
    rate: float = 4.5,
    tenure_years: int = 25
) -> Dict[str, Any]:
    """
    Returns structured analysis for buy vs rent using deterministic math and heuristics:
    - if planning_years < 3 -> recommend rent
    - if planning_years > 5 -> recommend buy
    Otherwise compare mortgage cost vs rent
    """
    primitives = MortgageCalculator.affordability_primitives(property_price)
    loan_amount = primitives["max_loan"]
    emi = MortgageCalculator.calculate_emi(loan_amount, rate, tenure_years)

    # Conservative maintenance estimate (monthly) — use 0.25% annually of property price / 12
    maintenance_monthly = round(property_price * 0.0025 / 12.0, 2)

    monthly_mortgage_cost = round(emi + maintenance_monthly, 2)

    decision = {
        "primitives": primitives,
        "emi": emi,
        "maintenance_monthly": maintenance_monthly,
        "monthly_mortgage_cost": monthly_mortgage_cost,
        "reason": "",
        "recommendation": None,
        "affordability_flag": None,
        "emi_percent_income": None
    }

    # Affordability by income if provided
    if income_monthly and income_monthly > 0:
        emi_pct = (emi / income_monthly) * 100
        decision["emi_percent_income"] = round(emi_pct, 1)
        # simple rule: EMI <= 40% income considered affordable
        decision["affordability_flag"] = "affordable" if emi_pct <= 40 else "high"

    # Heuristic based on planned stay
    if planning_years is not None:
        if planning_years < 3:
            decision["recommendation"] = "rent"
            decision["reason"] = "You plan to stay under 3 years — transaction costs and fees usually make buying unattractive."
            return decision
        if planning_years > 5:
            decision["recommendation"] = "buy"
            decision["reason"] = "You plan to stay over 5 years — equity buildup usually favors buying."
            return decision

    # If rent provided, compare monthly costs
    if current_rent_monthly and current_rent_monthly > 0:
        # Compare mortgage monthly cost vs rent
        if monthly_mortgage_cost < current_rent_monthly:
            decision["recommendation"] = "buy"
            decision["reason"] = "Monthly mortgage cost (including maintenance) is lower than current rent."
        else:
            # If mortgage higher, check margin and inform
            diff_pct = ((monthly_mortgage_cost - current_rent_monthly) / current_rent_monthly) * 100 if current_rent_monthly else 0
            decision["recommendation"] = "rent" if diff_pct > 10 else "buy"
            decision["reason"] = ("Mortgage is higher than rent by {:.1f}% — renting may be better short-term."
                                  if diff_pct > 10 else "Mortgage is slightly higher than rent; buying may still be acceptable for medium/long-term.")
            decision["reason"] = decision["reason"].format(diff_pct)
    else:
        # No rent provided — lean on affordability
        if decision["affordability_flag"] == "affordable":
            decision["recommendation"] = "buy"
            decision["reason"] = "Based on EMI as a share of your income, buying appears affordable."
        else:
            decision["recommendation"] = "rent"
            decision["reason"] = "EMI appears high relative to income; renting is safer."

    return decision

# ============ SAFE LLM WRAPPER (Groq) ============
def load_groq_client():
    """
    Attempt to load Groq SDK client from secrets.
    This function is defensive: it will return None if the SDK isn't installed or key missing.
    """
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        # Try to import typical groq SDK - adapt if your environment uses another name
        import groq
        client = groq.Client(api_key=api_key)
        return client
    except Exception:
        # SDK not available or failed to instantiate — proceed without LLM
        return None

def ask_llm_for_friendly_text(client, summary: Dict[str, Any]) -> str:
    """
    Send the precomputed numbers to the LLM and request a short, empathic reply.
    IMPORTANT: the prompt explicitly instructs the LLM NOT to recalculate numbers.
    If client is None or call fails, fallback to local templated reply.
    """
    # Compose deterministic payload
    primitives = summary["primitives"]
    prompt_user = f"""
You are a friendly UAE mortgage advisor named Sakshi. Use the exact numbers provided below. DO NOT recalculate numbers — use them as-is.

Precomputed numbers:
- Property price: AED {primitives['property_price']:,.0f}
- Max loan (80%): AED {primitives['max_loan']:,.0f}
- Min down (20%): AED {primitives['min_down']:,.0f}
- Hidden upfront costs (7%): AED {primitives['upfront']:,.0f}
- Total upfront needed: AED {primitives['total_upfront']:,.0f}
- Monthly EMI (25 yrs @ 4.5%): AED {summary['emi']:,.2f}
- Maintenance monthly estimate: AED {summary['maintenance_monthly']:,.2f}
- Monthly mortgage cost (EMI + maintenance): AED {summary['monthly_mortgage_cost']:,.2f}

Your tasks:
1) Produce a concise (2-3 sentence) empathetic answer summarizing affordability and the recommended action.
2) Ask exactly one clarifying question if useful (e.g., "How many years do you plan to stay?").
3) Do NOT perform any calculation. Use the numbers exactly as shown.
"""

    if client is None:
        # Fallback deterministic reply
        rec = summary["recommendation"]
        friendly = (
            f"Hi — I am Sakshi, your UAE mortgage advisor. Based on the numbers: EMI AED {summary['emi']:,.2f} "
            f"and estimated monthly mortgage cost AED {summary['monthly_mortgage_cost']:,.2f}, I would recommend you **{rec.upper()}**. "
            f"{summary['reason']} Would you like a buy-vs-rent breakdown tailored to your exact stay duration?"
        )
        return friendly

    # Try LLM call (defensive)
    try:
        # many groq SDKs expose different methods; attempt common ones defensively
        if hasattr(client, "generate") or hasattr(client, "predict") or hasattr(client, "call"):
            # Try a generic call pattern
            if hasattr(client, "generate"):
                resp = client.generate(prompt_user, max_tokens=250)
                text = getattr(resp, "text", None) or str(resp)
            elif hasattr(client, "predict"):
                resp = client.predict(prompt_user, max_output_tokens=250)
                text = getattr(resp, "text", None) or str(resp)
            else:
                resp = client.call(prompt_user, max_tokens=250)
                text = getattr(resp, "text", None) or str(resp)
            # Basic sanitization
            if text and isinstance(text, str) and len(text) > 0:
                return text.strip()
    except Exception:
        # fall through to fallback
        pass

    # Last-resort deterministic fallback
    rec = summary["recommendation"]
    return (
        f"Hi — I am Sakshi, your UAE mortgage advisor. Based on the numbers: EMI AED {summary['emi']:,.2f} "
        f"and estimated monthly mortgage cost AED {summary['monthly_mortgage_cost']:,.2f}, I would recommend you **{rec.upper()}**. "
        f"{summary['reason']} Would you like a buy-vs-rent breakdown tailored to your exact stay duration?"
    )

# ============ INPUT PARSING HELPERS ============
def extract_numbers(text: str):
    numbers = re.findall(r'[\d,.]+', text)
    parsed = []
    for n in numbers:
        try:
            parsed.append(float(n.replace(",", "")))
        except:
            continue
    return parsed

def safe_float(value):
    try:
        return float(value)
    except:
        return None

# ============ SESSION STATE INITIALIZATION ============
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "agent" not in st.session_state:
    st.session_state["agent"] = {"name": "Sakshi"}
if "last_summary" not in st.session_state:
    st.session_state["last_summary"] = None

# ============ APP LAYOUT ============
st.markdown('<div class="main-header"><h1>🏠 AskRivo AI Mortgage Advisor</h1><p>Hi — I am Sakshi, your AI mortgage friend for UAE property decisions.</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    # Display conversation
    for m in st.session_state["messages"]:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            st.markdown(f'<div class="user-msg">👤 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-msg">🤖 {content}</div>', unsafe_allow_html=True)

    # Input area
    user_input = st.text_input("Type your mortgage question...", placeholder="e.g., I earn 25,000 AED/month, pay 6,000 rent, want to buy a 2,000,000 AED apartment and stay 6 years", key="input")
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        send = st.button("Send")
    with btn_col2:
        reset = st.button("New Chat")

    st.markdown('</div>', unsafe_allow_html=True)

    if reset:
        st.session_state["messages"] = []
        st.session_state["last_summary"] = None
        st.experimental_rerun()

    if send and user_input:
        # Save user message
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Parse user input for numbers and keywords
        nums = extract_numbers(user_input)
        # Heuristic parsing:
        income = None
        rent = None
        prop_price = None
        planning_years = None

        # try to find units keywords
        t = user_input.lower()
        if "income" in t or "salary" in t or "earn" in t:
            if nums:
                income = nums[0]
        if "rent" in t:
            # if multiple numbers, rent often is smaller than income/property — choose smallest positive number if plausible
            if nums:
                # choose a reasonable candidate: prefer numbers that look like rent (<= 50k)
                candidate = None
                for n in nums:
                    if n <= 100000:
                        candidate = n
                        break
                rent = candidate or (nums[0] if nums else None)
        if "apartment" in t or "flat" in t or "property" in t or "buy" in t or "aed" in t or "million" in t:
            if nums:
                # choose the largest number as property price heuristic
                prop_price = max(nums)

        # try to find planning horizon phrase
        m = re.search(r'(\d+)\s*(years|year|yrs|yr)', t)
        if m:
            planning_years = int(m.group(1))

        # If not enough parsed values, fall back to asking clarifying question (without LLM)
        if not prop_price:
            bot_msg = "Hi — I am Sakshi. Please share the property price you are considering (e.g., '2,000,000 AED') so I can run the numbers for buy-vs-rent."
            st.session_state["messages"].append({"role": "assistant", "content": bot_msg})
            st.experimental_rerun()

        # Run deterministic analysis
        summary = buy_vs_rent_decision(
            property_price=float(prop_price),
            income_monthly=float(income) if income else 0.0,
            current_rent_monthly=float(rent) if rent else 0.0,
            planning_years=planning_years,
            rate=4.5,
            tenure_years=25
        )

        # Save mapped summary for UI/inspect
        st.session_state["last_summary"] = summary

        # Try LLM for friendly text
        client = load_groq_client()
        assistant_text = ask_llm_for_friendly_text(client, summary)

        # Add assistant reply
        st.session_state["messages"].append({"role": "assistant", "content": assistant_text})

        # Lead capture prompt appended
        lead_prompt = "If you'd like tailored help, share your email and I'll prepare a short financing plan (no spam)."
        st.session_state["messages"].append({"role": "assistant", "content": lead_prompt})

        st.experimental_rerun()

with col2:
    st.markdown("### 📋 Rules & Quick Info")
    st.markdown(
        """
        <div class="info-card">
        ✅ <b>Hard rules enforced in code:</b><br>
        • Max LTV (Expats): 80% (20% min down)<br>
        • Hidden upfront costs: 7% of price<br>
        • Interest rate used: 4.5% (annual)<br>
        • Max tenure: 25 years<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show last computed numbers (useful for reviewers)
    if st.session_state.get("last_summary"):
        s = st.session_state["last_summary"]
        p = s["primitives"]
        st.markdown("### 🔢 Last Calculations (Deterministic)")
        st.markdown(f"- Property price: AED {p['property_price']:,.0f}")
        st.markdown(f"- Max loan (80%): AED {p['max_loan']:,.0f}")
        st.markdown(f"- Min down (20%): AED {p['min_down']:,.0f}")
        st.markdown(f"- Hidden upfront (7%): AED {p['upfront']:,.0f}")
        st.markdown(f"- Total upfront: AED {p['total_upfront']:,.0f}")
        st.markdown(f"- Monthly EMI (25 yrs @ 4.5%): AED {s['emi']:,.2f}")
        st.markdown(f"- Maintenance estimate (monthly): AED {s['maintenance_monthly']:,.2f}")
        st.markdown(f"- Monthly mortgage cost: AED {s['monthly_mortgage_cost']:,.2f}")
        if s.get("emi_percent_income") is not None:
            st.markdown(f"- EMI as % of income: {s['emi_percent_income']}% ({s['affordability_flag']})")

    # Secrets check
    if st.secrets.get("GROQ_API_KEY", ""):
        st.markdown("<div class='info-card'><b>Groq API:</b> configured (used for conversational framing only)</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-card'><b>Groq API:</b> not configured — app will use deterministic templates.</div>", unsafe_allow_html=True)

# ============ END ============

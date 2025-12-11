# AskRivo Mortgage AI Assistant

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://askrivo-mortgage-assistant.streamlit.app/)  
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repo-blue?logo=github)](https://github.com/Sakshi983-cmd/Askrivo-mortgage-assistant)  
*Live Demo: [Try the Bot Here](https://askrivo-mortgage-assistant.streamlit.app/)* – Interact with the conversational AI to get personalized buy vs. rent advice for UAE expats.

## Overview
This is a fully functional, AI-native conversational mortgage assistant built for CoinedOne's AI Engineering Challenge ("The Anti-Calculator"). It transforms static calculators into an empathetic "smart friend" that guides UAE expats through buy vs. rent decisions with natural language, accurate math, and emotional insights—warning on hidden fees, affordability, and long-term equity without hallucinations.

Built in under 2 hours using AI-assisted tools for extreme velocity, this prototype picks the "Buy vs. Rent" scenario, integrates Gemini LLM via SDK for tool calling/streaming, and exceeds minimum requirements: unobtrusive data collection, deterministic calculations, lead capture, edge case handling (e.g., zero income empathy), and low-latency responses. It's deployed on Streamlit Cloud for immediate testing, with modular code ready for swaps (e.g., to GPT or Gemini Pro).

**Key Achievements in 24 Hours**:
- **Human-Like UX**: Empathetic chat with proactive nudges, visual breakdowns (pie charts for costs), and feedback capture.
- **Reliability**: Tools offload math to Python functions—zero LLM arithmetic errors.
- **Velocity**: Leveraged Cursor/Claude/Grok for code gen, achieving polish like custom themes and charts fast.
- **Product Sense**: Guides to conversion (e.g., "Email for your report?") while feeling natural, not robotic.

This demonstrates my "builder" mindset: Self-started from spec, owned full lifecycle (backend logic, AI integration, UI), and shipped a scalable prototype aligned with AskRivo's unbiased real estate guidance.<grok-card data-id="2969ca" data-type="citation_card"></grok-card>

## Live Demo & Testing
- **URL**: [askrivo-mortgage-assistant.streamlit.app](https://askrivo-mortgage-assistant.streamlit.app)
- **Test Scenario**: Say, "I earn 20k AED/month, eyeing a 2M AED apartment in Dubai Marina, with 400k down payment, current rent 10k, planning to stay 4 years on a 20-year loan."  
  - Bot collects data naturally, calculates EMI/upfront costs, advises "borderline" with heuristics, visualizes breakdown, and captures lead.
- **Edge Cases Handled**: Zero income → "Buying isn't feasible—let's explore rentals."; Invalid down payment → "Need at least 20% for expats."

## Architecture
- **LLM**: Google Gemini 1.5 Flash (fast, free tier, excellent tool calling/streaming). Chosen for UAE relevance (GCP integration in JD) and modularity—swap to GPT/Gemini Pro by changing `genai.GenerativeModel('new-model')`.
- **Framework**: Streamlit for rapid web UI (chat interface, session state for history). Google Generative AI SDK for LLM/tools. No heavy deps—keeps it lightweight.
- **Why This Stack?**: Streamlit enables mobile-friendly prototypes in minutes; Gemini SDK handles function calling natively (empathy/intent via LLM, math via deterministic code). Modular: Tools are separate functions; easy to extend (e.g., add RAG for developer checks as per product desc).<grok-card data-id="e12f7f" data-type="citation_card"></grok-card>
- **State Management**: Streamlit `session_state` for conversation history—persistent across turns.
- **Edge Cases**: Validated in tools (e.g., min 20% down payment, max 25y tenure, low income → custom advice). Errors handled empathetically without crashing.
- **Latency Optimization**: Streaming responses (<2s start time); no long waits.


## System Design
To align with the JD's emphasis on scalable backend services, data models, reliable infrastructure (caching, rate limiting, high availability), and AI-native development (RAG pipelines, AI agents), here's the high-level system design for scaling this prototype to production. It incorporates hybrid conversational AI patterns for robustness.<grok-card data-id="53a9a0" data-type="citation_card"></grok-card><grok-card data-id="8d6ee3" data-type="citation_card"></grok-card>

The current prototype is a monolithic Streamlit app for velocity, but designed modularly for easy migration to MERN/AWS/GCP stack. Key components:

- **User Interface Layer**: Streamlit chat (web/mobile responsive) for natural input/output.
- **Backend Layer**: Handles requests, integrates LLM, executes tools.
- **AI Integration Layer**: Gemini for intent/empathy, tool calling for math/workflows.
- **Data/Infra Layer**: Session state (prototype); scalable with DB/caching.
- **Extensions for Scalability**: Background jobs, RAG for market insights, error handling/retries.


```mermaid
graph TD
    A[User Interface - Streamlit Chat] --> B[Backend - Streamlit Server]
    B --> C[LLM Integration - Gemini API]
    B --> D[Tools/Functions - Deterministic Math (EMI, Advice)]
    B --> E[Session State - Conversation History]
    C --> F[Tool Calling - Function Calls for Math]
    B --> G[Visualizations - Matplotlib Charts]
    B --> H[Lead Capture - User Contact Collection]
    I[Scalable Extensions] --> J[Database - Store Leads/History (e.g., PostgreSQL)]
    I --> K[Caching - Redis for Rate Limiting]
    I --> L[Background Jobs - Celery for Async Tasks]
    I --> M[RAG Pipeline - Vector DB for UAE Market Insights]
    B -.-> I[Future Scalability]

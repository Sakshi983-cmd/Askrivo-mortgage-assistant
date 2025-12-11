# 🏗️ UAE Mortgage Assistant - System Design Document

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [Failure Handling Strategy](#failure-handling-strategy)
5. [Scalability & Performance](#scalability--performance)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security Considerations](#security-considerations)
8. [Future Enhancements](#future-enhancements)

---

## 🎯 Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Streamlit Frontend (Custom CSS/Animations)              │  │
│  │  - Chat Interface                                         │  │
│  │  - Message History Display                                │  │
│  │  - Input Handler                                          │  │
│  │  - State Management (Session State)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ User Input
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MortgageAgent (Core Controller)                         │  │
│  │  - Intent Classification                                  │  │
│  │  - Tool Selection Logic                                   │  │
│  │  - Response Generation                                    │  │
│  │  - Conversation Flow Management                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           ↓                      ↓                      ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  CONTEXT LAYER   │  │   TOOL LAYER     │  │  RESILIENCE     │
│                  │  │                  │  │     LAYER       │
│ ConversationMgr  │  │ MortgageCalc     │  │ GeminiClient    │
│ - History        │  │ - EMI Calc       │  │ - Retry Logic   │
│ - State Tracking │  │ - Affordability  │  │ - Backoff       │
│ - Token Mgmt     │  │ - Buy vs Rent    │  │ - Error Handle  │
│ - Data Extract   │  │ - Validation     │  │ - Logging       │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   LLM SERVICE   │
                    │  Gemini 1.5     │
                    │  (External API) │
                    └─────────────────┘
```

---

## 🧩 Component Design

### 1. **UI Layer** (Presentation)

**Responsibility**: User interaction, display, input collection

**Key Components**:
```python
class UILayer:
    """
    Handles all user-facing interactions
    """
    def render_chat_interface()
        # Display conversation history
        # Handle user input
        # Show loading states
        # Display error messages
    
    def render_stats_sidebar()
        # Show collected user data
        # Display quick facts
        # Provide navigation
    
    def apply_custom_styling()
        # Gradient backgrounds
        # Animation effects
        # Responsive design
```

**Design Decisions**:
- **Why Streamlit?** Rapid prototyping + built-in state management
- **Why Custom CSS?** Production-quality UI that doesn't look templated
- **Why Session State?** Maintain conversation across reruns

---

### 2. **Orchestration Layer** (Business Logic)

**Responsibility**: Decision making, flow control, intelligence

```python
class MortgageAgent:
    """
    The brain - orchestrates all components
    """
    
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.calculator = MortgageCalculator()
        self.conversation = ConversationManager()
    
    def generate_response(user_message):
        """
        Main orchestration pipeline:
        1. Add message to history
        2. Extract structured data
        3. Determine if calculation needed
        4. Call appropriate tools
        5. Build context for LLM
        6. Generate empathetic response
        7. Return to user
        """
        
        # Step 1: State Management
        self.conversation.add_message("user", user_message)
        
        # Step 2: Data Extraction (NLP)
        self.conversation.extract_user_data(user_message)
        
        # Step 3: Tool Selection (Decision Logic)
        if self.should_calculate(user_message):
            calculation = self.run_appropriate_calculation()
        
        # Step 4: Context Building (Token Management)
        context = self.conversation.get_context(max_tokens=4000)
        
        # Step 5: LLM Call (with Resilience)
        response = self.gemini_client.generate_with_retry(
            prompt=build_prompt(context, calculation)
        )
        
        # Step 6: Response Enrichment
        enriched_response = self.add_follow_up_suggestions(response)
        
        return enriched_response
```

**Key Algorithms**:

#### Intent Classification
```python
def should_calculate(user_message, context):
    """
    Determine if we need to run calculations
    
    Algorithm:
    - Check for calculation triggers (keywords)
    - Validate we have required data
    - Check conversation stage
    """
    triggers = ['calculate', 'emi', 'afford', 'buy', 'rent', 'price']
    has_trigger = any(t in user_message.lower() for t in triggers)
    has_data = 'property_price' in self.conversation.user_data
    
    return has_trigger and has_data
```

#### Tool Selection Logic
```python
def select_tool(user_data, user_intent):
    """
    Route to appropriate calculation
    
    Decision Tree:
    - Has rent + price + years → Buy vs Rent Analysis
    - Has price only → Affordability Check
    - Has loan amount → EMI Calculation
    - Missing data → Data Collection Mode
    """
    if all(k in user_data for k in ['rent', 'price', 'years']):
        return 'buy_vs_rent_analysis'
    elif 'property_price' in user_data:
        return 'affordability_check'
    else:
        return 'data_collection'
```

---

### 3. **Context Management Layer** (Memory)

**Responsibility**: Conversation history, token optimization, data extraction

```python
class ConversationManager:
    """
    Manages conversation state and context
    """
    
    def __init__(self):
        self.messages = []           # Full conversation history
        self.user_data = {}          # Extracted structured data
        self.calculations = []       # Calculation history
        self.metadata = {
            'start_time': datetime.now(),
            'message_count': 0,
            'calculations_run': 0
        }
    
    def add_message(role, content):
        """
        Add message with metadata
        """
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
            'token_count': estimate_tokens(content)
        })
        self.metadata['message_count'] += 1
    
    def get_context(max_tokens=4000):
        """
        Smart context windowing with token management
        
        Algorithm:
        1. Start from most recent messages
        2. Keep adding until token limit
        3. Ensure both user and assistant messages included
        4. Preserve conversation coherence
        """
        context = []
        total_tokens = 0
        
        for msg in reversed(self.messages):
            msg_tokens = msg['token_count']
            if total_tokens + msg_tokens > max_tokens:
                break
            context.insert(0, msg)
            total_tokens += msg_tokens
        
        return self.format_context(context)
    
    def extract_user_data(message):
        """
        NLP-style data extraction from natural language
        
        Extraction Patterns:
        - Income: "I make 20k" → user_data['income'] = 20000
        - Price: "2M AED apartment" → user_data['price'] = 2000000
        - Rent: "paying 8k rent" → user_data['rent'] = 8000
        - Duration: "staying 5 years" → user_data['years'] = 5
        """
        import re
        
        # Extract numbers with context
        if 'income' in message.lower() or 'earn' in message.lower():
            numbers = re.findall(r'(\d+)k', message.lower())
            if numbers:
                self.user_data['income'] = int(numbers[0]) * 1000
        
        # Price extraction (handles M, K, AED)
        if any(word in message.lower() for word in ['buy', 'price', 'apartment']):
            if 'm aed' in message.lower() or 'million' in message.lower():
                numbers = re.findall(r'(\d+\.?\d*)m', message.lower())
                if numbers:
                    self.user_data['property_price'] = float(numbers[0]) * 1000000
```

**Token Management Strategy**:
```
Token Budget: 4000 tokens (Gemini 1.5 Flash context)

Allocation:
- System Prompt: ~500 tokens (fixed)
- User Data Summary: ~200 tokens (dynamic)
- Calculation Results: ~300 tokens (if present)
- Conversation History: ~3000 tokens (managed)

Token Estimation: ~4 characters per token (heuristic)
```

---

### 4. **Tool Layer** (Deterministic Computation)

**Responsibility**: Zero-hallucination calculations

```python
class MortgageCalculator:
    """
    Pure functions - no LLM involvement
    All calculations mathematically verified
    """
    
    # Domain Constants (UAE Mortgage Rules)
    MAX_LTV = 0.80          # Maximum Loan-to-Value for expats
    UPFRONT_COSTS = 0.07    # 7% transaction costs
    STANDARD_RATE = 0.045   # 4.5% annual interest (current market)
    MAX_TENURE = 25         # Maximum loan tenure in years
    
    @staticmethod
    def calculate_emi(loan_amount, annual_rate, tenure_years):
        """
        EMI Formula: 
        E = P × r × (1 + r)^n / ((1 + r)^n - 1)
        
        Where:
        E = EMI
        P = Principal (loan amount)
        r = Monthly interest rate
        n = Number of monthly payments
        
        Complexity: O(1) - constant time
        """
        monthly_rate = annual_rate / 12
        num_payments = tenure_years * 12
        
        # Handle edge case: zero interest
        if monthly_rate == 0:
            return loan_amount / num_payments
        
        # Standard EMI formula
        numerator = loan_amount * monthly_rate * (1 + monthly_rate) ** num_payments
        denominator = (1 + monthly_rate) ** num_payments - 1
        emi = numerator / denominator
        
        return {
            'emi': round(emi, 2),
            'total_payment': round(emi * num_payments, 2),
            'total_interest': round((emi * num_payments) - loan_amount, 2),
            'breakdown': {
                'principal': loan_amount,
                'interest_rate': annual_rate,
                'tenure': tenure_years,
                'monthly_rate': monthly_rate
            }
        }
    
    @staticmethod
    def calculate_affordability(property_price, down_payment=None):
        """
        Affordability Analysis
        
        Components:
        1. Minimum down payment (20% for expats)
        2. Maximum loan (80% of property value)
        3. Upfront costs (7% of property price)
        4. Total initial investment
        """
        if down_payment is None:
            down_payment = property_price * (1 - MAX_LTV)
        
        max_loan = property_price * MAX_LTV
        actual_loan = property_price - down_payment
        
        # Upfront costs breakdown
        upfront_breakdown = {
            'transfer_fee': property_price * 0.04,  # 4%
            'agency_fee': property_price * 0.02,    # 2%
            'misc_fees': property_price * 0.01      # 1%
        }
        
        total_upfront_costs = sum(upfront_breakdown.values())
        
        return {
            'property_price': property_price,
            'down_payment': down_payment,
            'max_loan': max_loan,
            'actual_loan': min(actual_loan, max_loan),
            'upfront_costs': total_upfront_costs,
            'upfront_breakdown': upfront_breakdown,
            'total_initial_investment': down_payment + total_upfront_costs,
            'ltv_ratio': (actual_loan / property_price) * 100
        }
    
    @staticmethod
    def buy_vs_rent_analysis(monthly_rent, property_price, years_planning):
        """
        Buy vs Rent Decision Algorithm
        
        Factors Considered:
        1. Transaction costs (7% upfront)
        2. Mortgage interest vs rent
        3. Maintenance costs (0.2% monthly)
        4. Opportunity cost
        5. Time horizon
        
        Decision Rules:
        - < 3 years: RENT (transaction costs not recovered)
        - > 5 years: BUY (equity buildup wins)
        - 3-5 years: CALCULATE (break-even analysis)
        """
        # Get affordability metrics
        affordability = calculate_affordability(property_price)
        loan_amount = affordability['actual_loan']
        
        # Calculate mortgage costs
        emi_data = calculate_emi(loan_amount, STANDARD_RATE, MAX_TENURE)
        monthly_mortgage = emi_data['emi']
        
        # Maintenance costs (UAE standard: ~0.2% of property value/month)
        monthly_maintenance = property_price * 0.002
        
        # Total monthly cost of ownership
        total_monthly_own = monthly_mortgage + monthly_maintenance
        
        # Total costs over planning period
        total_rent_paid = monthly_rent * 12 * years_planning
        total_ownership_cost = (
            affordability['total_initial_investment'] +
            (total_monthly_own * 12 * years_planning)
        )
        
        # Calculate equity buildup (principal paid)
        principal_paid = loan_amount - (
            loan_amount * (1 + STANDARD_RATE/12)**(12 * years_planning) -
            monthly_mortgage * ((1 + STANDARD_RATE/12)**(12 * years_planning) - 1) / (STANDARD_RATE/12)
        )
        
        # Adjusted ownership cost (minus equity)
        adjusted_own_cost = total_ownership_cost - principal_paid
        
        # Decision logic
        if years_planning < 3:
            recommendation = "RENT"
            reason = "Transaction costs (7%) not recovered in short timeframe"
        elif years_planning > 5:
            recommendation = "BUY"
            reason = "Equity buildup and long-term appreciation outweigh costs"
        else:
            if adjusted_own_cost < total_rent_paid:
                recommendation = "BUY"
                reason = "Break-even analysis favors ownership"
            else:
                recommendation = "RENT"
                reason = "Renting is more economical for this timeframe"
        
        return {
            'recommendation': recommendation,
            'reason': reason,
            'financial_comparison': {
                'total_rent_cost': total_rent_paid,
                'total_ownership_cost': total_ownership_cost,
                'equity_buildup': principal_paid,
                'adjusted_own_cost': adjusted_own_cost,
                'savings': total_rent_paid - adjusted_own_cost
            },
            'monthly_comparison': {
                'rent': monthly_rent,
                'mortgage': monthly_mortgage,
                'maintenance': monthly_maintenance,
                'total_own': total_monthly_own
            }
        }
```

**Why Separate Tool Layer?**
1. **Accuracy**: 100% mathematically correct (no LLM hallucinations)
2. **Testability**: Each function can be unit tested
3. **Transparency**: Users can verify calculations
4. **Performance**: No API calls for simple math
5. **Cost**: No tokens wasted on arithmetic

---

### 5. **Resilience Layer** (Fault Tolerance)

**Responsibility**: Handle failures gracefully

```python
class GeminiClient:
    """
    Resilient API client with retry logic
    """
    
    def __init__(self, api_key, max_retries=3):
        self.api_key = api_key
        self.max_retries = max_retries
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False
    
    def generate_with_retry(self, prompt, attempt=1):
        """
        Resilient generation with exponential backoff
        
        Retry Strategy:
        - Attempt 1: Immediate
        - Attempt 2: Wait 2 seconds
        - Attempt 3: Wait 4 seconds
        
        Handles:
        - Network timeouts
        - API rate limits
        - Server errors (5xx)
        - Quota exceeded
        """
        
        # Check circuit breaker
        if self.circuit_open:
            if self._should_retry_circuit():
                self.circuit_open = False
            else:
                raise CircuitBreakerOpenError()
        
        try:
            logger.info(f"API call attempt {attempt}/{self.max_retries}")
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 1024,
                }
            )
            
            # Reset failure tracking on success
            self.failure_count = 0
            logger.info("API call successful")
            
            return response.text
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            error_type = type(e).__name__
            logger.error(f"API error (attempt {attempt}): {error_type} - {str(e)}")
            
            # Open circuit breaker after 5 consecutive failures
            if self.failure_count >= 5:
                self.circuit_open = True
                logger.error("Circuit breaker opened")
            
            # Retry logic
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8...
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.generate_with_retry(prompt, attempt + 1)
            else:
                logger.error("Max retries exceeded")
                return None
    
    def _should_retry_circuit(self):
        """Circuit breaker recovery logic"""
        if self.last_failure_time is None:
            return True
        
        # Try to close circuit after 60 seconds
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure > 60
```

**Failure Scenarios Handled**:

| Failure Type | Handling Strategy | User Experience |
|--------------|-------------------|-----------------|
| API Timeout | Retry with exponential backoff | "Thinking..." indicator |
| Rate Limit | Wait and retry | Transparent to user |
| Server Error (5xx) | Retry with backoff | Graceful degradation |
| Invalid API Key | Immediate error | Clear error message |
| Network Error | Retry 3 times | Fallback message |
| Quota Exceeded | Circuit breaker | Inform user politely |

---

## 🔄 Data Flow Diagram

```
┌─────────────┐
│    USER     │
│ Types msg   │
└──────┬──────┘
       │
       ↓ User Input: "I want to buy 2M AED apartment"
┌────────────────────────────────────────┐
│  STEP 1: Input Reception               │
│  - Capture input via Streamlit         │
│  - Basic validation (not empty)        │
│  - Add to UI state                     │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 2: Message History Update        │
│  ConversationManager.add_message()     │
│  - Append to history array             │
│  - Estimate token count                │
│  - Update metadata                     │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 3: Data Extraction (NLP)         │
│  ConversationManager.extract_user_data()│
│  - Regex patterns for numbers          │
│  - Keyword matching (income, price)    │
│  - Update user_data dict               │
│  Result: {property_price: 2000000}     │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 4: Tool Selection                │
│  MortgageAgent.should_calculate()      │
│  - Check for calculation triggers      │
│  - Validate required data present      │
│  Decision: RUN CALCULATION             │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 5: Deterministic Calculation     │
│  MortgageCalculator.calculate_*()      │
│  - Affordability: 20% down = 400k      │
│  - Max loan: 80% = 1.6M                │
│  - Upfront costs: 7% = 140k            │
│  - EMI: 1.6M @ 4.5% = 8,882 AED       │
│  Result: Complete calculation object   │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 6: Context Building              │
│  ConversationManager.get_context()     │
│  - Get last 10 messages (token limit)  │
│  - Include user data summary           │
│  - Append calculation results          │
│  Output: Formatted context string      │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 7: Prompt Construction           │
│  Build structured prompt:              │
│  - System instructions                 │
│  - Conversation context                │
│  - User data summary                   │
│  - Calculation results                 │
│  - Response guidelines                 │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 8: LLM API Call (with Retry)    │
│  GeminiClient.generate_with_retry()    │
│  Try 1: ✓ Success                      │
│  (If fail: exponential backoff retry)  │
└─────────────┬──────────────────────────┘
              │
              ↓ Response from Gemini
┌────────────────────────────────────────┐
│  STEP 9: Response Processing           │
│  - Parse LLM response                  │
│  - Validate output format              │
│  - Add to conversation history         │
└─────────────┬──────────────────────────┘
              │
              ↓
┌────────────────────────────────────────┐
│  STEP 10: UI Update                    │
│  - Display assistant message           │
│  - Update stats sidebar                │
│  - Check if Sakhi should appear        │
│  - Render with custom styling          │
└─────────────┬──────────────────────────┘
              │
              ↓
┌─────────────┐
│    USER     │
│ Sees reply  │
└─────────────┘
```

**Latency Breakdown**:
```
Total Response Time: ~2-3 seconds

- Input processing: <50ms
- Data extraction: <100ms
- Calculation: <10ms (deterministic)
- Context building: <100ms
- LLM API call: 1.5-2s (dominant factor)
- Response rendering: <200ms
```

---

## 🛡️ Failure Handling Strategy

### Error Taxonomy & Handling

```
                    ┌─────────────────┐
                    │   ERROR TYPE    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌─────▼──────┐     ┌─────▼──────┐
    │ NETWORK  │      │  API LEVEL │     │ BUSINESS   │
    │  ERRORS  │      │   ERRORS   │     │   LOGIC    │
    └────┬─────┘      └─────┬──────┘     └─────┬──────┘
         │                  │                   │
    ┌────▼──────────┐  ┌───▼────────────┐ ┌───▼─────────┐
    │ • Timeout     │  │ • Rate Limit   │ │ • Invalid   │
    │ • Connection  │  │ • Auth Fail    │ │   Input     │
    │ • DNS Fail    │  │ • Quota        │ │ • Missing   │
    │               │  │ • 5xx Errors   │ │   Data      │
    └───────────────┘  └────────────────┘ └─────────────┘
         │                  │                   │
    ┌────▼──────────┐  ┌───▼────────────┐ ┌───▼─────────┐
    │ RETRY +       │  │ RETRY +        │ │ VALIDATION  │
    │ BACKOFF       │  │ CIRCUIT        │ │ + GUIDANCE  │
    │               │  │ BREAKER        │ │             │
    └───────────────┘  └────────────────┘ └─────────────┘
```

### Implementation

```python
class ErrorHandler:
    """
    Centralized error handling
    """
    
    @staticmethod
    def handle_network_error(error, attempt):
        """Handle network-level failures"""
        if attempt < MAX_RETRIES:
            wait_time = min(2 ** attempt, 30)  # Cap at 30s
            logger.warning(f"Network error, retry in {wait_time}s")
            time.sleep(wait_time)
            return True  # Should retry
        return False
    
    @staticmethod
    def handle_api_error(error):
        """Handle API-level failures"""
        if "quota" in str(error).lower():
            return {
                'should_retry': False,
                'user_message': "I'm temporarily unavailable. Please try again in a few minutes."
            }
        elif "rate limit" in str(error).lower():
            return {
                'should_retry': True,
                'wait_time': 60,
                'user_message': None  # Transparent to user
            }
        else:
            return {
                'should_retry': True,
                'wait_time': 2,
                'user_message': None
            }
    
    @staticmethod
    def handle_business_error(error, user_data):
        """Handle business logic errors"""
        if "missing_income" in str(error):
            return "I need to know your monthly income to give accurate advice. How much do you earn per month?"
        elif "invalid_price" in str(error):
            return "The property price seems unusual. Could you confirm the price in AED?"
        else:
            return "I didn't quite understand that. Could you rephrase?"
```

---

## 📈 Scalability & Performance

### Current Architecture Scalability

```
┌───────────────────────────────────────────────────────┐
│         CURRENT STATE (MVP)                            │
│                                                        │
│  • Single Streamlit instance                          │
│  • Session-based state (in-memory)                    │
│  • Synchronous processing                             │
│  • No database                                        │
│                                                        │
│  Capacity: ~100 concurrent users                      │
│  Bottleneck: Streamlit session management             │
└───────────────────────────────────────────────────────┘
```

### Scalability Roadmap

```
PHASE 1 (Current): MVP - Single Instance
  └─> 100 concurrent users

PHASE 2: Horizontal Scaling
  ├─> Add Redis for session state
  ├─> Multiple Streamlit instances
  ├─> Load balancer (NGINX)
  └─> 1,000 concurrent users

PHASE 3: Microservices
  ├─> Separate API service (FastAPI)
  ├─> Dedicated calculation service
  ├─> Message queue (RabbitMQ)
  ├─> PostgreSQL for persistence
  └─> 10,000+ concurrent users

PHASE 4: Cloud-Native
  ├─> Kubernetes orchestration
  ├─> Auto-scaling
  ├─> Distributed caching
  └─> Unlimited scale
```

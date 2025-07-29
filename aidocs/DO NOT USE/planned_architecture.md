# Hybrid AI Agents + Managers Architecture

## Overview
This architecture combines AI agents for decision-making and data processing with traditional managers for technical operations. AI agents handle OpenAI/LLM interactions, while managers handle database, utilities, and formatting functions.

## Architecture Principles
1. **AI for Intelligence**: Agents use LLM for decision-making and data extraction
2. **Functions for Operations**: Managers provide hard-coded utility functions
3. **Clear Separation**: AI logic separated from technical operations
4. **Conversation Persistence**: Full context storage with conversation resumption
5. **Consistent Data Flow**: All agents receive raw text uniformly

## Architecture Layers

### AI Agents Layer (LLM-powered decision making)

#### 1. OrchestratorAgent (orchestrator_agent.py)
**Responsibility**: Main decision maker and request router

**Functions**:
- Analyze user input via OpenAI API
- Determine request type: operational vs informational
- Route to appropriate sub-agent
- Manage overall conversation flow

**Decision Logic**:
```python
def analyze_request(self, text: str, context: dict) -> str:
    # Uses OpenAI to determine:
    # - Operation: expense, income, transfer, adjustment
    # - Information: analytics, statements, reports
    # - Other: general questions, help requests
```

**Communication**:
- Input: Raw text + conversation context
- Output: Routing decision + processed request
- Calls: OperationAgents or InformationAgent

#### 2. OperationAgents (4 types)

##### ExpenseAgent (expense_agent.py)
**Responsibility**: Handle expense operations using AI

**Functions**:
- Extract expense data from raw text via OpenAI
- Identify missing required fields
- Generate clarifying questions
- Validate extracted data

##### IncomeAgent (income_agent.py)
**Responsibility**: Handle income operations using AI

**Functions**:
- Extract income data from raw text via OpenAI
- Identify missing required fields
- Generate clarifying questions
- Validate extracted data

##### TransferAgent (transfer_agent.py)
**Responsibility**: Handle transfer operations using AI

**Functions**:
- Extract transfer data from raw text via OpenAI
- Identify missing required fields (from_account, to_account, amount)
- Generate clarifying questions
- Validate extracted data

##### AdjustmentAgent (adjustment_agent.py)
**Responsibility**: Handle adjustment operations using AI

**Functions**:
- Extract adjustment data from raw text via OpenAI
- Identify missing required fields (account, amount, reason)
- Generate clarifying questions
- Validate extracted data

#### 3. InformationAgent (information_agent.py)
**Responsibility**: Handle analytical and informational requests using AI

**Functions**:
- Analyze user requests for information via OpenAI
- Generate analytical reports and statements
- Answer complex financial questions
- Create comparisons and summaries

**Example Requests**:
- "Show my expenses for last month"
- "Compare my spending this month vs last month"
- "What's my current balance on cash account?"
- "Which categories did I spend money on last week?"
- "Prepare analytics for me"

### Manager Layer (Hard-coded functions)

#### 4. ConversationManager (conversation_manager.py)
**Responsibility**: Bridge between users and AI agents - ONLY component that handles database operations (not AI-powered)

**Functions**:
- Create new conversation with unique ID (1, 2, 3...)
- Store conversation state and agent interactions in database
- Update database in real-time during agent conversations
- Manage conversation lifecycle from start to completion
- Link conversation_id to Google Sheets row ID
- **Provide full conversation context to agents** - agents understand what's happening through ConversationManager


**Conversation Lifecycle Management**:
```python
# Step 1: Create conversation
conversation_id = ConversationManager.create_conversation(user_id, chat_id)

# Step 2: Agent asks question
ConversationManager.update_conversation_state(
    conversation_id, 
    agent_question="С какого счета?",
    partial_data={"amount": 300, "item": "coffee"}
)

# Step 3: User responds
ConversationManager.store_user_response(conversation_id, "Наличные")

# Step 4: Operation complete
ConversationManager.mark_conversation_complete(
    conversation_id, 
    google_sheets_row=7  # Actual row where data was inserted
)
```

#### 5. InputProcessor (input_processor.py)
**Responsibility**: Input processing utilities

**Functions**:
- Process voice messages using Whisper API
- Extract text from images using OpenAI Vision API
- Handle file downloads and conversions
- Return standardized text output

#### 6. MessageFormatter (message_formatter.py)
**Responsibility**: Response formatting utilities

**Functions**:
- **Strict formatting**: When applying/editing operations in Google Sheets
  ```python
  format_operation_confirmation(operation_data) -> str:
      # Returns: "Записал: Расход 300₽, категория Кофе, счет Наличные"
  ```
- **Free formatting**: For informational responses (very compact)
  ```python
  format_analytics_response(data) -> str:
      # Returns natural, compact analytical text
  ```

## Data Flow

### Message Processing Flow
```
1. User sends message (voice/text/image)
2. InputProcessor converts to text
3. ConversationManager creates new conversation with unique ID
   - Creates database record with conversation_id (1, 2, 3...)
   - This ID will be linked to Google Sheets row later
4. OrchestratorAgent analyzes text via OpenAI and makes routing decision
5. Decision point:
   ├── Operation → Route to OperationAgent (Expense/Income/Transfer/Adjustment)
   └── Information → Route to InformationAgent
6. Selected OperationAgent (e.g., ExpenseAgent):
   a. Analyzes raw text via OpenAI
   b. Identifies missing data (e.g., missing account)
   c. If incomplete: Returns question to ConversationManager
7. ConversationManager:
   a. Updates database with agent question and partial data
   b. Sends question to user
   c. Waits for user reply
8. User provides missing information
9. ConversationManager:
   a. Updates database with user response
   b. Passes complete data back to ExpenseAgent
10. ExpenseAgent:
    a. Validates all data is complete
    b. Calls google_utilities.insert_expense_to_sheets(data)
    c. Returns success confirmation
11. ConversationManager:
    a. Updates database: marks conversation complete
    b. Stores Google Sheets row reference
12. MessageFormatter creates confirmation response
13. Send confirmation to user
```

### Conversation Context Management
```python
# ConversationManager stores by conversation_id:
{
    "conversation_id": 123,
    "user_id": "telegram_user_id",
    "chat_id": "telegram_chat_id",
    "operation_type": "expense",
    "agent_state": "ExpenseAgent",
    "partial_data": {
        "amount": 300,
        "item": "coffee"
    },
    "missing_fields": ["account", "category"],
    "message_history": [
        {"user": "купил кофе", "message_id": 101, "timestamp": "2025-07-27T15:30:00"},
        {"bot": "Какая сумма?", "message_id": 102, "timestamp": "2025-07-27T15:30:01"},
        {"user": "300 рублей", "reply_to": 102, "timestamp": "2025-07-27T15:30:15"}
    ],
    "last_bot_message_id": 102,
    "created_at": "2025-07-27T15:30:00",
    "updated_at": "2025-07-27T15:30:15"
}
```

### Conversation Resumption
```python
# User can resume week-old conversation:
old_conversation = ConversationManager.resume_conversation(conversation_id)
# Loads full context including:
# - Partial operation data
# - Message history  
# - Agent state
# - Missing fields
# Agent continues from exact same state
```

### Reply Mechanism
```
message_id: Current message ID from Telegram
reply_to_message_id: Previous bot message ID (for context linking)

Flow:
1. User replies to bot message
2. ConversationManager uses reply_to_message_id to fetch conversation_id
3. Load full conversation context
4. Route to appropriate agent with full context
5. Agent continues conversation from previous state
```

## Key Architecture Rules

### Database Operations Rule
**ONLY ConversationManager handles database operations**:
- AI Agents (ExpenseAgent, IncomeAgent, etc.) do NOT interact with database
- AI Agents work with raw text and return results to ConversationManager
- ConversationManager updates database in real-time during conversations
- ConversationManager creates unique conversation_id linked to Google Sheets row

### Agent Communication Rule
```python
# ❌ WRONG: Agent accessing database directly
class ExpenseAgent:
    def process(self, text):
        data = self.extract_data(text)
        database.store(data)  # ❌ Agents don't touch database

# ✅ CORRECT: Agent returns data to ConversationManager
class ExpenseAgent:
    def process(self, text):
        data = self.extract_data(text)
        return data  # ✅ ConversationManager handles database
```

## Example Conversations

### Detailed Operation Flow with Database Operations
```
1. User: "Купил кофе за 300 рублей"
2. ConversationManager: Creates conversation_id=123 in database
3. ConversationManager: Provides full context to OrchestratorAgent
4. OrchestratorAgent: Analyzes text → determines "expense operation"
5. ConversationManager: Provides full context to ExpenseAgent
6. ExpenseAgent: Extracts data → amount=300, item=coffee, missing=[account, category]
7. ConversationManager: Updates database with partial data and question
8. Bot: "С какого счета?" (message_id: 102)

9. User: "Наличные" (reply_to_message_id: 102)
10. ConversationManager: Updates database with user response, provides full context to ExpenseAgent
11. ExpenseAgent: Merges data → amount=300, item=coffee, account=cash, missing=[category]
12. ConversationManager: Updates database with new question
13. Bot: "В какую категорию?"

14. User: "Кофе" 
15. ConversationManager: Updates database with final user response, provides complete context to ExpenseAgent
16. ExpenseAgent: Complete data → calls google_utilities.insert_expense_to_sheets()
17. Google Sheets: Returns row number 7 (actual insertion row)
18. ConversationManager: Updates database - marks complete, stores Google Sheets row=7
19. MessageFormatter: "Записал: Расход 300₽, категория Кофе, счет Наличные"
```

### Information Flow
```
User: "Сколько я потратил на кофе за последнюю неделю?"
OrchestratorAgent: Determines → information request
InformationAgent: Analyzes request via OpenAI
InformationAgent: Calls google_utilities.get_expenses_by_category("Кофе", "last_week")
InformationAgent: Processes data via OpenAI for natural response
MessageFormatter: Free format → "За неделю на кофе потрачено 2,100₽ (7 покупок)"
```

### Conversation Resumption
```
[Week ago conversation was interrupted]
User: "Продолжим про тот расход"
ConversationManager: Finds old conversation_id by context
ConversationManager: Loads full historical context
ExpenseAgent: Resumes from exact state where left off
Bot: "Мы обсуждали расход 300₽ на кофе. Нужно указать счет. С какого счета?"
```

## Directory Structure
```
src/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── orchestrator_agent.py
│   ├── expense_agent.py
│   ├── income_agent.py
│   ├── transfer_agent.py
│   ├── adjustment_agent.py
│   └── information_agent.py
├── managers/
│   ├── __init__.py
│   ├── conversation_manager.py
│   ├── input_processor.py
│   └── message_formatter.py
├── database/
│   ├── connection.py
│   ├── models.py
│   └── migrations/
├── config/
│   └── settings.yaml
├── server.py
└── run_server.py
```

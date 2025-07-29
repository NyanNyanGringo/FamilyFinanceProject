# Database Architecture for Hybrid AI Agents + Managers System

## Overview
This document defines the database architecture for the planned hybrid system where AI agents handle intelligence operations while managers handle database operations. The architecture centers around conversation persistence and real-time state management.

## Core Design Principles

1. **Single Responsibility**: Only ConversationManager performs database operations
2. **Conversation Persistence**: Full conversation context stored with resumption capability
3. **Real-time Updates**: Database updated immediately during agent interactions
4. **Message Linking**: Direct relationship between conversations and Telegram messages
5. **Google Sheets Integration**: Conversations linked to actual Google Sheets rows

## Database Schema

### Primary Tables

#### conversations
Core table storing conversation state and lifecycle.

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    operation_type TEXT,  -- 'expense', 'income', 'transfer', 'adjustment', 'information'
    agent_state TEXT,     -- 'ExpenseAgent', 'IncomeAgent', etc.
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'completed', 'abandoned'
    google_sheets_row INTEGER,  -- Actual row number where data was inserted
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_chat ON conversations(user_id, chat_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_created ON conversations(created_at);
```

#### conversation_data
Stores partial and complete operation data as JSON.

```sql
CREATE TABLE conversation_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    data_type TEXT NOT NULL,  -- 'partial', 'complete', 'missing_fields'
    data_content TEXT NOT NULL,  -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversation_data_conv_id ON conversation_data(conversation_id);
CREATE INDEX idx_conversation_data_type ON conversation_data(data_type);
```

#### message_history
Complete message history for conversation context and resumption.

```sql
CREATE TABLE message_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    message_id INTEGER,  -- Telegram message ID
    reply_to_message_id INTEGER,  -- For threading
    sender TEXT NOT NULL,  -- 'user' or 'bot'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_message_history_conv_id ON message_history(conversation_id);
CREATE INDEX idx_message_history_message_id ON message_history(message_id);
CREATE INDEX idx_message_history_reply_to ON message_history(reply_to_message_id);
```

#### agent_questions
Tracks questions asked by AI agents during data collection.

```sql
CREATE TABLE agent_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    question TEXT NOT NULL,
    missing_fields TEXT,  -- JSON array of missing field names
    asked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    answered_at DATETIME,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_agent_questions_conv_id ON agent_questions(conversation_id);
CREATE INDEX idx_agent_questions_agent ON agent_questions(agent_name);
```

### Auxiliary Tables

#### user_sessions
Tracks user activity and context for better conversation management.

```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    last_conversation_id INTEGER,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    timezone TEXT DEFAULT 'UTC',
    FOREIGN KEY (last_conversation_id) REFERENCES conversations(id)
);

CREATE UNIQUE INDEX idx_user_sessions_user_chat ON user_sessions(user_id, chat_id);
```

#### operation_templates
Stores frequently used operation patterns for AI training.

```sql
CREATE TABLE operation_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    template_name TEXT NOT NULL,
    sample_input TEXT NOT NULL,
    expected_output TEXT NOT NULL,  -- JSON
    usage_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_operation_templates_type ON operation_templates(operation_type);
```

## Data Models and Relationships

### Core Data Flow

```python
# Example conversation lifecycle in database

# 1. Create new conversation
conversation_id = db.execute("""
    INSERT INTO conversations (user_id, chat_id, operation_type, agent_state)
    VALUES (?, ?, ?, ?)
""", user_id, chat_id, "expense", "ExpenseAgent")

# 2. Store initial message
db.execute("""
    INSERT INTO message_history (conversation_id, message_id, sender, content)
    VALUES (?, ?, 'user', ?)
""", conversation_id, telegram_message_id, ":C?8; :>D5 70 300 @C1;59")

# 3. Store partial data from AI agent
db.execute("""
    INSERT INTO conversation_data (conversation_id, data_type, data_content)
    VALUES (?, 'partial', ?)
""", conversation_id, json.dumps({"amount": 300, "item": "coffee"}))

# 4. Store agent question
db.execute("""
    INSERT INTO agent_questions (conversation_id, agent_name, question, missing_fields)
    VALUES (?, 'ExpenseAgent', '! :0:>3> AG5B0?', ?)
""", conversation_id, json.dumps(["account", "category"]))

# 5. Store bot response
db.execute("""
    INSERT INTO message_history (conversation_id, message_id, sender, content)
    VALUES (?, ?, 'bot', '! :0:>3> AG5B0?')
""", conversation_id, bot_message_id)

# 6. Store user reply
db.execute("""
    INSERT INTO message_history (conversation_id, message_id, reply_to_message_id, sender, content)
    VALUES (?, ?, ?, 'user', '0;8G=K5')
""", conversation_id, user_reply_message_id, bot_message_id)

# 7. Update conversation data
db.execute("""
    INSERT INTO conversation_data (conversation_id, data_type, data_content)
    VALUES (?, 'partial', ?)
""", conversation_id, json.dumps({"amount": 300, "item": "coffee", "account": "cash"}))

# 8. Mark conversation complete
db.execute("""
    UPDATE conversations 
    SET status = 'completed', google_sheets_row = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
""", sheets_row_number, conversation_id)

# 9. Store final complete data
db.execute("""
    INSERT INTO conversation_data (conversation_id, data_type, data_content)
    VALUES (?, 'complete', ?)
""", conversation_id, json.dumps({
    "amount": 300, 
    "item": "coffee", 
    "account": "cash", 
    "category": "coffee",
    "google_sheets_row": 7
}))
```

### Conversation Context Structure

```python
# Complete conversation context loaded by ConversationManager
conversation_context = {
    "conversation_id": 123,
    "user_id": "telegram_user_id",
    "chat_id": "telegram_chat_id",
    "operation_type": "expense",
    "agent_state": "ExpenseAgent",
    "status": "active",
    
    # Latest partial data
    "partial_data": {
        "amount": 300,
        "item": "coffee",
        "account": "cash"
    },
    
    # What's still missing
    "missing_fields": ["category"],
    
    # Complete message thread
    "message_history": [
        {
            "id": 1,
            "message_id": 101,
            "sender": "user",
            "content": ":C?8; :>D5 70 300 @C1;59",
            "timestamp": "2025-07-27T15:30:00"
        },
        {
            "id": 2,
            "message_id": 102,
            "sender": "bot",
            "content": "! :0:>3> AG5B0?",
            "timestamp": "2025-07-27T15:30:01"
        },
        {
            "id": 3,
            "message_id": 103,
            "reply_to_message_id": 102,
            "sender": "user",
            "content": "0;8G=K5",
            "timestamp": "2025-07-27T15:30:15"
        }
    ],
    
    # Agent interaction history
    "agent_questions": [
        {
            "agent_name": "ExpenseAgent",
            "question": "! :0:>3> AG5B0?",
            "missing_fields": ["account", "category"],
            "asked_at": "2025-07-27T15:30:01",
            "answered_at": "2025-07-27T15:30:15"
        }
    ],
    
    "created_at": "2025-07-27T15:30:00",
    "updated_at": "2025-07-27T15:30:15",
    "last_bot_message_id": 102
}
```

## Key Database Operations

### ConversationManager Database Methods

```python
class ConversationManager:
    
    def create_conversation(self, user_id: str, chat_id: str) -> int:
        """Creates new conversation and returns conversation_id"""
        
    def update_conversation_state(self, conversation_id: int, **kwargs):
        """Updates conversation with partial data, agent questions, etc."""
        
    def store_user_response(self, conversation_id: int, content: str, message_id: int, reply_to: int = None):
        """Stores user message in message_history"""
        
    def store_bot_message(self, conversation_id: int, content: str, message_id: int):
        """Stores bot message in message_history"""
        
    def get_conversation_context(self, conversation_id: int) -> dict:
        """Returns complete conversation context for AI agents"""
        
    def find_conversation_by_reply(self, reply_to_message_id: int) -> int:
        """Finds conversation_id by bot message being replied to"""
        
    def mark_conversation_complete(self, conversation_id: int, google_sheets_row: int):
        """Marks conversation as completed and stores Google Sheets reference"""
        
    def resume_conversation(self, conversation_id: int) -> dict:
        """Loads full historical context for conversation resumption"""
        
    def get_user_active_conversations(self, user_id: str, chat_id: str) -> list:
        """Returns all active conversations for user"""
        
    def store_final_operation_data(self, conversation_id: int, complete_data: dict):
        """Stores complete operation data after Google Sheets insertion"""
```

## Database Integration Points

### With AI Agents
- **ConversationManager** provides complete context to agents
- Agents return decisions and extracted data
- ConversationManager stores all agent interactions in real-time
- No direct database access from AI agents

### With Google Sheets
- Conversations linked to Google Sheets rows via `google_sheets_row` field
- Enables tracking which conversation created which data entry
- Supports data auditing and conversation history

### With Telegram
- Message IDs stored for threading and reply context
- Reply mechanism enables conversation resumption
- User sessions tracked for context persistence

## Performance Considerations

### Indexing Strategy
- Primary indexes on conversation lookups (`user_id`, `chat_id`)
- Message threading indexes (`message_id`, `reply_to_message_id`)
- Temporal indexes for analytics and cleanup

### Data Retention
```sql
-- Cleanup old completed conversations (>30 days)
DELETE FROM conversations 
WHERE status = 'completed' 
AND updated_at < datetime('now', '-30 days');

-- Archive old conversation data
INSERT INTO conversation_archive 
SELECT * FROM conversations 
WHERE status = 'completed' 
AND updated_at < datetime('now', '-7 days');
```

### Optimization
- JSON data in `data_content` allows flexible schema evolution
- Separate tables for different data types enable efficient queries
- Message history enables context reconstruction without API calls

## Migration Strategy

### Phase 1: Database Setup
1. Create tables and indexes
2. Initialize ConversationManager
3. Test basic conversation lifecycle

### Phase 2: Integration
1. Connect with existing Google Sheets utilities
2. Integrate with Telegram message handling
3. Implement conversation resumption

### Phase 3: AI Agent Integration
1. Connect agents to ConversationManager
2. Implement context passing
3. Test complete conversation flows

This database architecture provides the foundation for the hybrid AI system with full conversation persistence, resumption capabilities, and clear separation between AI decision-making and database operations.
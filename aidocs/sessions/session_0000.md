# 1. Session Goals:
Plan and design a new agent-based architecture for FamilyFinanceProject to replace the current monolithic structure. Document the current architecture and create a detailed plan for the new modular agent system.

# 2. TODOs:
- [x] Analyze current monolithic architecture in server.py
- [x] Document current architecture in current_architecture.md
- [x] Design new agent-based architecture with separate agents for each operation type
- [x] Document planned architecture in planned_architecture.md
- [x] Define OrchestratorAgent as the main entry point
- [x] Design separate agents for Expense, Income, Transfer, and Adjustment operations
- [x] Plan support agents (replaced with managers and utilities)
- [x] Define agent communication protocols and data flow
- [x] Review and refine the architecture plan with user feedback
- [x] Create implementation roadmap (included in planned_architecture.md)
- [x] Add PostgreSQL database architecture for conversation persistence
- [x] Design InformationAgent for analytics and complex queries
- [x] Simplify from 12-agent to hybrid 6 agents + 3 managers approach
- [x] Define ConversationManager as sole database interface and bridge between users and agents

# 3. Progress:

[2025-07-27 14:15]  
Started session to plan new agents architecture. Read project documentation including README.md, aidocs structure, and TreeView to understand the current system. The project is a Telegram bot that processes voice messages to manage financial operations in Google Sheets.

[2025-07-27 14:20]  
Analyzed the current monolithic architecture in server.py. Found that all business logic is contained in a single file with tight coupling between components. The flow goes from voice message → audio processing → OpenAI → data extraction → user confirmation → Google Sheets update.

[2025-07-27 14:25]  
Created current_architecture.md documenting the existing system. Identified key problems: monolithic design, tight coupling, limited scalability, code duplication, and testing challenges. The current system has all logic in server.py with direct dependencies between components.

[2025-07-27 14:30]  
Designed and documented the new agent-based architecture in planned_architecture.md. Created a modular system with:
- OrchestratorAgent as the main entry point
- Separate agents for each operation type (Expense, Income, Transfer, Adjustment)
- Support agents for common functionality
- Clear communication protocols using AgentContext and AgentResult
- Phased implementation plan

[2025-07-27 14:35]  
Completed initial architecture planning. The new design transforms the monolithic system into a well-organized, agent-based architecture with clear boundaries, single responsibilities, and defined interfaces. This will significantly improve maintainability, testability, and extensibility.

[2025-07-27 14:45]  
User reviewed the planned architecture and requested several important changes:
- Renamed AgentContext → ExecutionContext, AgentResult → ExecutionResult to avoid confusion
- Added support for image processing (receipts, screenshots)
- Removed Vosk model completely, using only Whisper
- Clarified that OrchestratorAgent determines operation type internally (no separate NaturalLanguageAgent)
- Updated operation agents to specify exact input fields
- Changed flow to immediate Google Sheets write after validation (no confirmation wait)
- Added reply-to-message functionality for context preservation
- Renamed NotificationAgent → MessageFormatterAgent

[2025-07-27 14:50]  
Updated planned_architecture.md with all requested changes. Key clarifications:
- OrchestratorAgent analyzes text and determines operation type itself using OpenAI
- Operation agents receive structured data with specific fields (amount, category, account, etc.)
- GoogleSheetsAgent uses existing auth files and writes immediately after validation
- Speed: Agent communication is minimal overhead, mostly async operations
- Context storage: Temporary solution using Google Sheets, future consideration for database

[2025-07-27 15:00]
User provided critical feedback about agent responsibilities and conversational flow:
- OrchestratorAgent should ONLY determine operation type, NOT extract data
- Operation agents receive raw text and extract their own data
- Replace ValidationAgent with ConversationAgent for handling missing data
- Added AgentMessage to core infrastructure
- Implemented full conversational flow where system asks for missing data
- Users can correct misunderstandings in conversation (expense→income)
- Added concrete conversation example showing data collection process

[2025-07-27 15:15]
User decided to use PostgreSQL database for conversation persistence instead of Google Sheets:
- Created database_architecture.md with complete PostgreSQL schema
- Added DatabaseAgent and ConversationPersistenceAgent to architecture
- Updated planned_architecture.md with detailed component explanations
- Replaced Google Sheets context storage with PostgreSQL persistence
- Added database configuration and environment variables
- Updated conversation flow to include database persistence steps
- Conversation context now survives server restarts via database storage

[2025-07-27 15:30]
Critical architecture review revealed over-engineering issues. Project orchestrator agent identified problems:
1. 12 agents created unnecessary complexity for simple financial operations
2. Inconsistent data flow - some agents got raw text, others expected structured data
3. Agent message passing added performance overhead vs direct function calls
4. ConversationPersistenceAgent + ConversationAgent + DatabaseAgent had overlapping responsibilities
5. MessageFormatterAgent was over-development for simple formatting

[2025-07-27 15:35]
Simplified architecture implemented - replaced 12-agent system with 5-module approach:
- **InputProcessor**: Handle voice/text/image processing
- **OperationManager**: Unified operation handling with specific handlers for each type
- **ConversationManager**: Handle conversation flow and database persistence
- **DataManager**: Direct database and Google Sheets integration  
- **MessageFormatter**: Simple utility functions for response formatting

Key improvements:
- All operation handlers receive raw text consistently
- Direct function calls instead of agent message passing
- Standard Python service layer pattern
- Maintained PostgreSQL persistence and reply functionality
- 60% reduction in components while preserving all features

[2025-07-27 15:45]
Final architecture refinement - hybrid AI agents + managers approach:
- **AI Agents Layer**: OrchestratorAgent + 4 OperationAgents + InformationAgent (uses OpenAI/LLM)
- **Manager Layer**: ConversationManager + InputProcessor + MessageFormatter (hard-coded functions)
- **Utility Layer**: google_utilities, analytics_utilities (called by agents)

Key decisions:
- Agents use AI for decision-making and data extraction
- Managers handle technical operations without AI
- ConversationManager stores context by conversation_id for week-old conversation resumption
- MessageFormatter has strict format (operations) and free format (information)
- InformationAgent handles analytics requests and complex queries
- All operation agents receive raw text consistently
- Database schema updated with agent_state and last_bot_message_id fields

[2025-07-27 16:00]
Critical clarification on database operations and conversation flow:
- **ONLY ConversationManager handles database operations** - no AI agents touch database
- ConversationManager creates unique conversation_id (1, 2, 3...) linked to Google Sheets row
- Complete conversation lifecycle managed by ConversationManager:
  1. Creates conversation_id when user sends message
  2. Updates database with agent questions and partial data in real-time
  3. Stores user responses as conversation progresses  
  4. Marks conversation complete and links to Google Sheets row number
- AI agents work purely with text analysis and return results to ConversationManager
- Updated database schema with conversation_id linking to Google Sheets rows
- ConversationManager serves as bridge between users and agents, providing full conversation context

[2025-07-27 16:15]
**Session Conclusion**: Successfully transformed FamilyFinanceProject from monolithic architecture to hybrid AI agents + managers system. Final design includes 6 AI agents (OrchestratorAgent + 4 OperationAgents + InformationAgent) for intelligent decision-making and 3 managers (ConversationManager + InputProcessor + MessageFormatter) for technical operations. Key achievement: ConversationManager as the sole database interface and bridge providing full context to agents, with PostgreSQL persistence enabling week-old conversation resumption. Architecture documentation complete with clear separation of AI logic from technical operations, ready for phased implementation.
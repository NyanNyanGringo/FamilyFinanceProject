# Product Requirements Document (PRD)
# FamilyFinanceProject

## Overview

FamilyFinanceProject is a Telegram bot that manages personal finances through natural language processing. Users interact via voice or text messages to track expenses, incomes, and transfers in a Google Sheets backend.

## Core Functionality

### Multi-Agent Architecture

The system uses an orchestrator agent that routes requests to specialized agents:
- **Main Orchestrator**: Analyzes user intent and delegates to appropriate agents
- **Expense Agent**: Processes expense transactions
- **Income Agent**: Processes income transactions
- **Transfer Agent**: Handles transfers and account adjustments
- **Query Agent**: Responds to balance inquiries and generates reports
- **Utility Agent**: Manages backups and system settings

### Transaction Management

#### Supported Operations
1. **Expenses**: Track spending with category, account, amount, and optional comments
2. **Incomes**: Record earnings with source category and destination account
3. **Transfers**: Move money between accounts with currency conversion
4. **Adjustments**: Correct account balances

#### Transaction Features
- Automatic processing without confirmation buttons
- Natural language understanding for all operations
- Multi-transaction support in single message (using "firstly", "secondly")
- Transaction history with Telegram message ID tracking

### Reply-Based Editing

Users can modify or delete transactions by replying to bot messages:
- Edit any field: amount, category, account, status, comment
- Delete transactions with audit trail
- No time restrictions on edits
- Changes applied immediately without preview

### Advanced Features

#### Financial Analytics
- Monthly expense breakdowns by category
- Account balance tracking
- Income vs expense comparisons
- Custom period reports
- Export to PDF and CSV formats

#### Budget Management
- Set monthly budgets by category
- Real-time spending alerts
- Overspending notifications
- Budget progress visualization

#### Duplicate Detection
- Identifies potential duplicate transactions (same amount, category, account within 5 minutes)
- Asks for user confirmation before creating duplicates
- Works across all transaction types

#### Automatic Backups
- Monthly automatic backup on 1st day of month
- Creates full spreadsheet copy in Google Drive
- Sends notification with backup link
- Manual backup available on demand

### Voice Recognition

- Primary language: Russian
- Context-aware recognition using transaction patterns
- Learns user preferences (e.g., "coffee" → 300 in Food category)
- Voice shortcuts for common operations
- Fallback to text when recognition confidence is low

## User Experience

### Natural Language Examples
- "Spent 50 dollars on groceries from credit card"
- "Transfer 1000 from savings to checking"
- "Income 5000 salary to main account"
- "Adjust wallet balance to 500"
- "Show my spending this month"
- "What's my total balance?"

### Response Handling
- Immediate transaction creation
- Clear confirmation with transaction details
- Telegram message ID stored for future edits
- No manual confirmation buttons required

## Data Storage

### Google Sheets Structure
- **Expenses Sheet**: Date, Category, Account, Amount, Status, Comment, Message ID
- **Incomes Sheet**: Date, Category, Account, Amount, Status, Comment, Message ID
- **Transfers Sheet**: Date, Type, From Account, To Account, Amounts, Status, Comment, Message ID

### Data Privacy
- No personal information stored in sheets
- Only financial transaction data
- Telegram user ID for identification
- No sensitive authentication data

## Non-Financial Commands

- Balance inquiries for specific accounts
- Spending reports by period or category
- Budget status checks
- Help and usage instructions
- Manual backup triggers
- System settings management

## Error Handling

- Invalid categories/accounts: Suggest closest matches
- Missing data: Request clarification
- Network failures: Retry with queuing
- Voice recognition issues: Fallback to text
- Duplicate entries: Confirmation prompt

## Performance Requirements

- Transaction processing: < 3 seconds
- Voice recognition: < 2 seconds
- Report generation: < 5 seconds
- Concurrent message handling
- Category/account list caching (5-minute TTL)

## Integration Requirements

### External Services
- Telegram Bot API for messaging
- Google Sheets API for data storage
- Google Drive API for backups
- OpenAI API for natural language processing
- Whisper API for voice transcription

### Environment Variables
- `TELEGRAM_TOKEN`: Bot authentication
- `GOOGLE_SPREADSHEET_ID`: Target spreadsheet
- `OPENAI_API_KEY`: AI processing

## Future Considerations

- Multi-currency portfolio tracking
- Recurring transaction support
- Financial goal tracking
- Category-based spending limits
- Investment tracking
- Banking API integrations
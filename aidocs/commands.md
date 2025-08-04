# Bot Commands Documentation

## Overview
The FamilyFinanceProject bot supports both voice messages and text commands. Commands provide quick access to specific functionality without needing to send voice messages.

## Available Commands

### /expenses_status
**Purpose**: Display current month's expense breakdown by category

**Usage**: Simply type `/expenses_status` in the chat

**Functionality**:
- Reads data from the `/expenses_status` sheet in Google Sheets
- Shows expenses by category with actual vs expected amounts
- Displays total monthly expenses
- Updates automatically as new expenses are added

**Response Format**:
```
Господин, траты по категориям в этом месяце:

Продукты - 15,000 из 20,000 RUB
Транспорт - 3,500 из 5,000 RUB
Развлечения - 8,000 из 10,000 RUB

Всего: 26,500 RUB
```

**Data Source**:
- Sheet: `/expenses_status`
- A2: Currency code
- B2:B: Category names
- C2:C: Actual amounts
- D2:D: Expected amounts
- E2: Total amount

### /memory
**Purpose**: Manage saved memory instructions that are used as priority context for all bot operations

**Usage**: Type `/memory` in the chat

**Functionality**:
- Shows all saved memories with numbered list
- Provides inline keyboard buttons to delete individual memories
- Memories are used as priority instructions for all LLM operations
- Empty state shows helpful message about adding memories

**Adding Memories**:
- Send any message starting with `#` to save it as a memory
- Example: `#Always use RUB currency for all operations`
- The text after `#` will be saved to the memory sheet

**Response Format**:
```
📝 Сохранённые воспоминания:

1. Always use RUB currency
2. Round all amounts to nearest 100
3. Use Продукты category for food expenses

Выберите воспоминание для удаления:
[❌ Удалить 1] [❌ Удалить 2] [❌ Удалить 3]
[✅ Готово]
```

**Data Source**:
- Sheet: `#memory`
- Cell A1: All memories stored as text, separated by newlines
- Integration: Memories are automatically included in all OpenAI API calls

## Command Features

### Auto-completion
All commands support Telegram's built-in auto-completion:
- Type `/` to see available commands
- Commands show descriptions in the suggestion list
- Implemented via `BotCommand` registration on startup

### Error Handling
Commands include proper error handling:
- Connection errors show user-friendly messages
- Missing data handled gracefully
- Loading indicators while fetching data

## Implementation Details

### Command Registration
Commands are registered in `set_bot_commands()` function:
```python
commands = [
    BotCommand("expenses_status", "Показать расходы за текущий месяц"),
    BotCommand("memory", "Управление сохранёнными воспоминаниями"),
]
```

### Handler Structure
Each command has a dedicated handler function:
- Receives `Update` and `Context` objects
- Sends initial "Loading..." message
- Fetches data from Google Sheets
- Formats and sends response
- Handles errors gracefully

## Future Commands (Planned)

### /income_status
- Show monthly income by source
- Compare to expected income

### /balance
- Show current account balances
- Display by currency

### /transfer_history
- Recent transfers between accounts
- Filter by date range

### /help
- List all available commands
- Show usage examples

## Adding New Commands

To add a new command:
1. Create handler function in `server.py`
2. Register with `CommandHandler` in main
3. Add to `set_bot_commands()` for auto-completion
4. Document in this file

## Best Practices

### Command Design
- Keep commands simple and focused
- Use descriptive names
- Provide loading feedback
- Handle errors gracefully

### Data Access
- Use dedicated Google Sheets tabs
- Cache data when appropriate
- Minimize API calls

### User Experience
- Respond quickly with initial message
- Edit message with results (avoid spam)
- Use clear, formatted text
- Support multiple languages
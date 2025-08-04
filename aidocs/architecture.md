# Current Architecture

## Overview
The FamilyFinanceProject is a monolithic Telegram bot application that processes voice messages to manage financial operations in Google Sheets. The architecture follows a procedural design pattern with direct function calls and tightly coupled components.

## System Flow

### 1. Entry Point
- `run_server.py` initializes the environment and starts the server
- `server.py` contains all business logic in a single module
- Bot commands are registered for auto-completion in Telegram

### 2. Message Processing Flow

```
User Voice Message � Telegram Bot � Voice Handler � Audio Processing � OpenAI � Google Sheets (Autosave)
```

### 3. Command Processing Flow

```
User Command � Command Handler � Google Sheets � Formatted Response
```

#### Text Message Processing (Memory)
```
User Text (#prefix) � Telegram Bot � Memory Text Handler � Google Sheets (#memory)
```

#### Detailed Steps:
1. **Voice Message Reception** (`voice_message_handler`)
   - Receives voice message from Telegram
   - Downloads and converts audio file (OGA � WAV)

2. **Audio to Text Conversion**
   - Uses either Whisper (OpenAI) or Vosk for speech recognition
   - Configured via `Audio2TextModels` class

3. **Operation Type Detection**
   - First OpenAI API call to determine operation type
   - Validates if the request is relevant
   - Splits multiple operations if needed

4. **Data Extraction**
   - Second OpenAI API call to extract structured data
   - Uses specific response formats for each operation type

5. **Data Validation** (`clarify_request_message`)
   - Validates categories, accounts, and statuses
   - Marks invalid fields with validation text

6. **Automatic Save to Google Sheets**
   - Voice messages are now autosaved immediately after validation
   - Telegram message IDs are stored in columns L, M, K for tracking
   - Creates `RequestData` object based on operation type
   - Executes batch update to Google Sheets

7. **User Confirmation/Deletion**
   - Sends formatted message with Delete button
   - Delete button shows confirmation prompt
   - Second click confirms deletion from Google Sheets
   - Uses telegram_message_id to locate and delete the row

## Key Components

### server.py
- **Main Module**: Contains all business logic
- **Functions**:
  - `voice_message_handler`: Main entry point for voice messages (with autosave)
  - `button_click_handler`: Router for button callbacks
  - `memory_button_handler`: Handles memory-related button operations
  - `operation_button_handler`: Handles financial operation buttons
  - `memory_text_handler`: Processes text messages starting with "#"
  - `memory_command_handler`: Handles /memory command
  - `expenses_status_handler`: Handles /expenses_status command
  - `clarify_request_message`: Validates extracted data
  - `format_json_to_telegram_text`: Formats responses
  - `set_bot_commands`: Registers bot commands for auto-completion
  - Various utility functions

- **Command Handlers**:
  - `/expenses_status`: Shows monthly expense breakdown by category
  - `/memory`: Manages saved memory instructions

### Utilities (lib/utilities/)
- **openai_utilities.py**: OpenAI API integration
  - Text-to-text conversion
  - Audio-to-text conversion
  - Response format definitions
  - Request builders
  - `_get_memory_context()`: Integrates memories into all API calls

- **google_utilities.py**: Google Sheets integration
  - Authentication
  - Batch updates
  - Enums for categories, operations, etc.
  - `delete_row_by_telegram_id`: Deletes rows using telegram message ID
  - Column references: expenses (AK), incomes (AL)
  - Memory functions: `get_memories()`, `add_memory()`, `delete_memory()`
  - ListName enum includes all sheet names

- **telegram_utilities.py**: Telegram-specific functions
- **ffmpeg_utilities.py**: Audio conversion
- **vosk_utilities.py**: Alternative speech recognition

## Data Models

### Operation Types
- Expenses (@0AE>4K)
- Incomes (4>E>4K)
- Transfers (?5@52>4K)
- Adjustments (:>@@5:B8@>2:8)

### Key Classes/Enums
- `OperationTypes`: Enum for operation types
- `Category`: Manages expense/income categories
- `Status`: Operation statuses (confirmed/planned)
- `RequestData`: Data model for Google Sheets updates

## Current Architecture Problems

1. **Monolithic Design**
   - All logic in single server.py file
   - Difficult to test individual components
   - Hard to maintain and extend

2. **Tight Coupling**
   - Direct dependencies between components
   - No clear separation of concerns
   - Business logic mixed with infrastructure

3. **Limited Scalability**
   - Cannot handle operations independently
   - No modularity for adding new features
   - Sequential processing only

4. **Error Handling**
   - Basic error handling
   - Difficult to recover from partial failures
   - Limited logging and monitoring

5. **Code Duplication**
   - Similar logic repeated for different operation types
   - No reusable components
   - Hardcoded response formatting

6. **Testing Challenges**
   - Difficult to unit test
   - Dependencies on external services
   - No mock interfaces

## Dependencies
- Python 3.10
- telegram (python-telegram-bot)
- OpenAI API
- Google Sheets API
- ffmpeg (system dependency)
- Vosk (optional)

## Configuration
- Environment variables in .env file
- Google credentials in google_credentials folder
- Vosk models in models folder (optional)
- Docker volumes for voice messages persistence

## Recent Updates

### Voice Message Autosave (July 2025)
- All valid voice messages are automatically saved to Google Sheets
- Telegram message IDs tracked in columns L, M, K
- Two-step delete process with confirmation
- Replaced Accept/Decline buttons with single Delete button

### Commands System (August 2025)
- Added `/expenses_status` command for monthly expense tracking
- Implemented command auto-completion in Telegram
- Commands read data from dedicated Google Sheets tabs

### Infrastructure Improvements
- Fixed Docker Poetry installation caching
- Voice messages directory as Docker volume
- Improved error handling for permissions

### Memory System (August 2025)
- Added text message handler for messages starting with "#"
- Implemented /memory command for managing saved instructions
- Store memories in "#memory" sheet, cell A1
- Memories used as priority context for all OpenAI API calls
- Two-way interaction: save via # prefix, manage via /memory command

### Code Refactoring (August 2025)
- Separated button_click_handler into three specialized handlers:
  - button_click_handler: Main router
  - memory_button_handler: Memory operations
  - operation_button_handler: Financial operations
- Moved hardcoded sheet names to ListName enum
- Improved code organization following Single Responsibility Principle
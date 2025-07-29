# Current Architecture

## Overview
The FamilyFinanceProject is a monolithic Telegram bot application that processes voice messages to manage financial operations in Google Sheets. The architecture follows a procedural design pattern with direct function calls and tightly coupled components.

## System Flow

### 1. Entry Point
- `run_server.py` initializes the environment and starts the server
- `server.py` contains all business logic in a single module

### 2. Message Processing Flow

```
User Voice Message � Telegram Bot � Voice Handler � Audio Processing � OpenAI � Google Sheets
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

6. **User Confirmation**
   - Sends formatted message with inline keyboard
   - Waits for user to confirm or reject

7. **Google Sheets Update** (`button_click_handler`)
   - Creates `RequestData` object based on operation type
   - Executes batch update to Google Sheets

## Key Components

### server.py
- **Main Module**: Contains all business logic
- **Functions**:
  - `voice_message_handler`: Main entry point for voice messages
  - `button_click_handler`: Handles user confirmations
  - `clarify_request_message`: Validates extracted data
  - `format_json_to_telegram_text`: Formats responses
  - Various utility functions

### Utilities (lib/utilities/)
- **openai_utilities.py**: OpenAI API integration
  - Text-to-text conversion
  - Audio-to-text conversion
  - Response format definitions
  - Request builders

- **google_utilities.py**: Google Sheets integration
  - Authentication
  - Batch updates
  - Enums for categories, operations, etc.

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
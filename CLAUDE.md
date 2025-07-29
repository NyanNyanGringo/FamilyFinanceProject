# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FamilyFinanceProject is a Python Telegram bot that manages financial operations in Google Sheets using natural language voice messages. The bot processes voice inputs, converts them to text using OpenAI's Whisper API, analyzes them with GPT models to extract financial data, and updates corresponding Google Sheets.

## Core Architecture

### Monolithic Structure
- **Entry Point**: `run_server.py` - Loads environment and starts the server
- **Main Logic**: `src/server.py` - Contains all business logic in a single 500+ line file
- **Utilities**: `lib/utilities/` - Modular utility functions for different services

### Key Components
- **Voice Processing**: OGA → WAV conversion → Whisper/Vosk → Text
- **AI Analysis**: Two-stage OpenAI processing (operation type detection → data extraction)
- **Data Validation**: Category/account validation against Google Sheets data
- **User Confirmation**: Telegram inline keyboard for approval
- **Google Sheets Integration**: Batch updates using Google Sheets API

## Development Commands

### Running the Application
```bash
# Install dependencies
poetry install

# Run the server
python run_server.py
```

### Dependencies Management
```bash
# Add new dependencies
poetry add <package_name>

# Update dependencies
poetry update
```

### Documentation Generation
```bash
# Generate API documentation
poetry run pdoc
```

Note: There are no formal linting, testing, or build commands configured in this project.

## Environment Setup

### Required Environment Variables (.env file)
- `OPENAI_API_KEY` - OpenAI API key for Whisper and GPT models
- `TELEGRAM_TOKEN` - Telegram bot token
- `GOOGLE_SPREADSHEET_ID` - Google Sheets document ID

### Google Authentication
- Place `credentials.json` from Google Cloud Project in `google_credentials/` folder
- `token.json` will be auto-generated on first run after OAuth flow

### Optional Components
- **FFmpeg**: Required for audio conversion (system dependency)
- **Vosk Models**: Place in `models/` folder for offline speech recognition
  - Default model: `vosk-model-small-ru-0.22`
  - Alternative: `vosk-model-ru-0.42`

## Code Structure

### Main Processing Flow (`src/server.py`)
1. `voice_message_handler()` - Main entry point for voice messages
2. `get_text_from_audio()` - Audio to text conversion
3. First OpenAI call - Operation type detection and validation
4. Second OpenAI call - Structured data extraction per operation type
5. `clarify_request_message()` - Data validation against Google Sheets
6. User confirmation via Telegram inline keyboard
7. `button_click_handler()` - Final Google Sheets update

### Utility Modules (`lib/utilities/`)
- **openai_utilities.py**: OpenAI API integration, response format definitions
- **google_utilities.py**: Google Sheets API, authentication, enums for categories/operations
- **telegram_utilities.py**: Telegram-specific functions
- **ffmpeg_utilities.py**: Audio file conversion
- **vosk_utilities.py**: Alternative speech recognition
- **date_utilities.py**: Date formatting for Google Sheets
- **log_utilities.py**: Logging configuration

### Operation Types
- **Expenses** (@0AE>4K) - Financial outflows
- **Incomes** (4>E>4K) - Financial inflows  
- **Transfers** (?5@52>4K) - Money movement between accounts
- **Adjustments** (:>@@5:B8@>2:8) - Balance corrections

### Data Models
- `OperationTypes` - Enum for operation types
- `Category` - Expense/income categories from Google Sheets
- `Status` - Operation status (confirmed vs planned)
- `RequestData` - Structured data for Google Sheets updates
- `ListName` - Google Sheets tab names
- `TransferType` - Transfer vs adjustment operations

## Google Sheets Integration

### Sheet Structure
- **Expenses Sheet**: Date | Category | Account | Amount | Status | Comment
- **Incomes Sheet**: Date | Category | Account | Amount | Status | Comment  
- **Transfers Sheet**: Date | Type | Source Account | Target Account | Source Amount | Target Amount | Status | Comment

### Configuration Ranges
Categories, accounts, and other configuration data are read from specific ranges in Google Sheets to maintain data consistency.

## Important Development Notes

### Current Architecture Limitations
- Monolithic design with all logic in `server.py`
- Tight coupling between components
- Limited error handling and recovery
- No unit tests or formal testing framework
- Sequential processing only

### Dependencies
- Python 3.10+ required
- Poetry for dependency management
- External services: OpenAI API, Google Sheets API, Telegram Bot API
- System dependency: FFmpeg for audio conversion

### Audio Processing
- Supports two models: Whisper (default) and Vosk (offline)
- Voice messages stored in `voice_messages/` directory
- OGA format converted to WAV for processing

### Logging
- Configured in `run_server.py` with INFO level
- Custom logger utility in `lib/utilities/log_utilities.py`
- HTTP requests logged at DEBUG level

### File Paths
- Configuration: `config.py` for constants
- Credentials: `google_credentials/` folder
- Audio files: `voice_messages/` folder
- Models: `models/` folder for Vosk models (optional)

## Development Strategies
- Try to use claude subagents as much as possible
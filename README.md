# FamilyFinanceProject


###### Python 3.10
###### Requires: OpenAI API-key, Google Tables OAuth 2.0 Client ID and Telegram Bot Token


### Description:
FamilyFinanceProject is a Telegram bot that manages custom financial Google Sheet.

Core features:

* Create, edit and delete all types of financial operations (incomes, expenses, transfers, adjustments)
* Use natural language to search, analyze and summarise all the information from Google Sheet like: balance, certain category expenses, account amounts, debts etc.
* Notifications about: subscriptions, payment periods etc.
* Weekly, monthly deep breakdowns
* Weekly Google Sheet backup

Main idea:

User use Google Sheets as financial database and dashboard platform. All the operations take place inside Telegram via voice and text messages. 


### Installation:

1. Clone the repository:
```
git clone https://github.com/NyanNyanGringo/FamilyFinanceProject.git
```

2. Install dependencies:
```
poetry install
```

3. Install ffmpeg:
```
# windows
winget install ffmpeg

# macos
brew install ffmpeg

# linux
sudo apt-get install ffmpeg
```

4. Rename the `.env.example` file to `.env` and specify the required values in it:
```
cp .env.example .env
```

5. Place `credentials.json` file from your Google Cloud Project to google_credentials folder.
After running app you have to authorize in Google and `token.json` file will be automatically
created in the same directory.

6. (optional) Place the necessary vosk models in the models folder
(if you don't plan to use vosk and prefer whisper, skip this step):
```
Download models: https://github.com/alphacep/vosk-space/blob/master/models.md

Example structure:
/models
- /vosk-model-small-ru-0.22
```

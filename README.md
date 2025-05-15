# FamilyFinanceProject

###### Python 3.10
###### Requires: OpenAI API-key, Google Tables OAuth 2.0 Client ID and Telegram Bot Token

### From Author:
Project for personal goals.  
Most likely you will find some usefully code.
It will not be possible to use the project as a ready-made solution,
since access to a Google Sheets custom template for financial management is required.

### Installation:

Clone the repository:
```
git clone https://github.com/NyanNyanGringo/FamilyFinanceProject.git
```

Install dependencies:
```
poetry install
```

#### Install ffmpeg:

##### For Windows:
```
Download ffmpeg: https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2024-09-12-14-07

Version: Auto-Build 2024-09-12 14:07 (or later)

Build used for Windows: ffmpeg-master-latest-win64-gpl.zip

Example structure:
/ffmpeg
- /bin
- /doc
- /LICENSE.txt
```

##### For macOS:
```
brew install ffmpeg
```
The application will automatically find the ffmpeg in your PATH.

##### For Linux:
```
# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

Rename the `.env.example` file to `.env` and specify the required values in it.

Place `credentials.json` file from your Google Cloud Project to google_credentials folder.
After running app you have to authorize in Google and `token.json` file will be automatically
created in the same directory.

Place the necessary vosk models in the models folder
(if you don't plan to use vosk and prefer whisper, skip this step):
```
Download models: https://github.com/alphacep/vosk-space/blob/master/models.md

Example structure:
/models
- /vosk-model-small-ru-0.22
```

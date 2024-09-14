# FamilyFinanceProject

###### Python 3.10
###### Requires API keys from OpenAI, Google Tables and TelegramBot

### From Author:
Project for personal goals.  
Most likely you will find some usefully code.
It will not be possible to use the project as a ready-made solution,
since access to a Google Sheets custom template for financial management is required.

### Installation:

Clone the repository:
```
git clone https://your-repository-link-here.git
```

Install dependencies:
```
poetry install
```

Install ffmpeg at the root of the project:
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

Rename the `.env.example` file to `.env` and specify the required values in it.

Place the necessary vosk models in the models folder
(if you don't plan to use vosk and prefer whisper, skip this step):
```
Download models: https://github.com/alphacep/vosk-space/blob/master/models.md

Example structure:
/models
- /vosk-model-small-ru-0.22
```

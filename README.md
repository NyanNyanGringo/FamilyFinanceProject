# FamilyFinanceProject


###### Python 3.10
###### Требуется: OpenAI API key, OAuth 2.0 Client ID для Google Sheets и токен Telegram-бота


### Описание:
FamilyFinanceProject — это Telegram-бот, который управляет пользовательской финансовой таблицей в Google Sheets.

Основные возможности:

* Создавать, редактировать и удалять все типы финансовых операций (доходы, расходы, переводы, корректировки)
* Использовать естественный язык, чтобы искать, анализировать и суммировать информацию из Google Sheets: баланс, расходы по конкретной категории, суммы по счетам, долги и т. д.
* Уведомления о подписках, периодах оплаты и т. п.
* Еженедельные и ежемесячные подробные разборы
* Еженедельный бэкап Google Sheets

Основная идея:

Пользователь использует Google Sheets как финансовую базу данных и платформу для дашборда. Все операции происходят внутри Telegram через голосовые и текстовые сообщения.


### Установка:

1. Клонируйте репозиторий:
```
git clone https://github.com/NyanNyanGringo/FamilyFinanceProject.git
```

2. Установите зависимости:
```
poetry install
```

3. Установите ffmpeg:
```
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

4. Переименуйте файл `.env.example` в `.env` и укажите в нём необходимые значения:
```
cp .env.example .env
```

5. Поместите файл `credentials.json` из вашего Google Cloud Project в папку `google_credentials`.
После запуска приложения нужно будет авторизоваться в Google — файл `token.json` будет автоматически
создан в той же директории.

6. (опционально) Поместите необходимые модели Vosk в папку `models`
(если вы не планируете использовать Vosk и предпочитаете Whisper — пропустите этот шаг):
```
Скачать модели: https://github.com/alphacep/vosk-space/blob/master/models.md

Пример структуры:
/models
- /vosk-model-small-ru-0.22
```

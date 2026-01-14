# Руководство по развёртыванию FamilyFinanceProject в Docker

Простая Docker-настройка для запуска Telegram-бота на VDS/VPS серверах.

## 🚀 Быстрый старт (локальное тестирование)

```bash
# 1. Клонируйте репозиторий
git clone <your-repo-url>
cd FamilyFinanceProject

# 2. Настройте окружение
cp .env.example .env
# Отредактируйте .env и укажите ваши ключи

# 3. Добавьте Google-креды
# Поместите файл .google_service_account_credentials.json в корень проекта

# 4. Запустите
docker-compose up -d
```

## 🖥️ Развёртывание на VDS/VPS

### 🚀 Развёртывание одной командой (рекомендуется)

Использует Docker Context для удобного удалённого деплоя:

```bash
# 1. Запустите скрипт деплоя (первичная настройка + деплой)
./deploy-simple.sh myvps

# 2. Для обновления просто запустите снова
./deploy-simple.sh myvps
```

Скрипт:
- Спросит IP вашего VPS и SSH-пользователя
- Автоматически создаст Docker context
- Задеплоит бота на VPS
- Вернёт контекст обратно на локальную машину

**Требования:**
- Доступ по SSH-ключу к вашему VPS
- Установленный Docker на VPS (скрипт может помочь с установкой)

### 📋 Ручная настройка VDS (альтернатива)

<details>
<summary>Нажмите, чтобы раскрыть шаги ручной настройки</summary>

#### Шаг 1: Установите Docker на VDS

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Шаг 2: Разверните проект на VDS

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd FamilyFinanceProject
```

#### Шаг 3: Настройте окружение (файл .env)

Создайте файл `.env` на VDS:
```bash
nano .env
```

Добавьте ваши креды:
```bash
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_TOKEN=your_telegram_bot_token_here
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id_here
```

#### Шаг 4: Настройте Google-креды

Создайте файл с кредами на VDS:
```bash
nano .google_service_account_credentials.json
```

Вставьте JSON сервисного аккаунта Google (полное содержимое файла с кредами).

#### Шаг 5: Деплой

```bash
# Создайте директорию для голосовых сообщений
mkdir -p voice_messages

# Запустите бота
docker-compose up -d

# Посмотрите логи
docker-compose logs -f
```

</details>

## 📋 Основные команды

```bash
# Запустить бота
docker-compose up -d

# Остановить бота
docker-compose down

# Посмотреть логи
docker-compose logs -f

# Перезапустить бота
docker-compose restart

# Проверить статус
docker-compose ps

# Проверка здоровья
docker exec familyfinance-bot /usr/local/bin/healthcheck.sh
```

## 🔧 Режим разработки

Для разработки с «живыми» обновлениями кода:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🐛 Устранение проблем

### Бот не запускается
```bash
# Проверьте логи на ошибки
docker-compose logs

# Проверьте переменные окружения
docker exec familyfinance-bot env | grep -E "(OPENAI|TELEGRAM|GOOGLE)"

# Проверьте файл с кредами
docker exec familyfinance-bot cat /app/.google_service_account_credentials.json
```

### Высокое использование диска
```bash
# Проверьте размер voice_messages
docker exec familyfinance-bot du -sh /app/voice_messages

# Ручная очистка (удалить файлы старше 7 дней)
docker exec familyfinance-bot find /app/voice_messages -type f -mtime +7 -delete
```

### Обновить бота
```bash
# Через деплой одной командой
./deploy-simple.sh myvps

# Или вручную
git pull
docker-compose build
docker-compose up -d
```

## 📁 Структура файлов

```
FamilyFinanceProject/
├── .env                                     # Ваши API-ключи
├── .google_service_account_credentials.json  # Google-креды
├── docker-compose.yml                        # Продакшен-настройки
├── docker-compose.dev.yml                    # Настройки для разработки
├── Dockerfile                               # Конфигурация контейнера
├── voice_messages/                          # Аудиофайлы (создаётся автоматически)
└── src/                                     # Код приложения
```

## ⚠️ Важные заметки

- **Голосовые файлы накапливаются** — следите за местом на диске и при необходимости очищайте вручную
- **Держите креды в безопасности** — никогда не коммитьте `.env` и файлы с кредами в git
- **Бот работает через polling** — не нужно открывать порты или настраивать webhooks
- **Контейнер автоматически перезапускается** — если бот упадёт, он стартует снова

## 🆘 Поддержка

Если бот не работает:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все 3 переменные окружения заданы корректно
3. Убедитесь, что JSON с Google-кредами валиден
4. Убедитесь, что ваш Google Sheet расшарен на email сервисного аккаунта

---

**Готово! Теперь ваш бот должен быть запущен на VDS! 🤖**

# 1. Цели сессии:
[Ожидается ввод пользователя с целями сессии]

# 2. TODO:
- [x] Исправить AttributeError в global_error_handler при обработке NoneType.message
- [x] Добавить обработку таймаутов с retry-логикой для вызовов Telegram API

# 3. Прогресс:
[2025-08-10 11:58]  
Исправили критические проблемы обработки ошибок в Telegram-боте:
- Убрали AttributeError в global_error_handler (src/server.py:419-424): безопасно проверяем, что update.callback_query существует, прежде чем обращаться к его message
- Добавили retry-логику для таймаутов Telegram API в voice_message_handler (src/server.py:778-800): 3 попытки с задержкой 2 секунды
- Добавили недостающие импорты: asyncio и TimedOut из telegram.error
- Теперь бот корректно переживает сетевые таймауты и не падает из‑за AttributeError в error handler

import logging
import os

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Логируем ошибку
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Проверяем, есть ли update и сообщение в нем
    if isinstance(update, Update) and update.message:
        try:
            # Пытаемся отправить пользователю сообщение об ошибке
            await update.message.reply_text("Произошла ошибка при обработке вашего запроса. "
                                            "Пожалуйста, попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")


async def example_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Пример вызова исключения для проверки
    raise ValueError("Это тестовая ошибка")


def run() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Устанавливаем глобальный обработчик ошибок
    application.add_error_handler(global_error_handler)

    # Добавляем обработчик, который генерирует ошибку
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, example_handler))

    # Запускаем приложение
    application.run_polling(allowed_updates=Update.ALL_TYPES)


run()

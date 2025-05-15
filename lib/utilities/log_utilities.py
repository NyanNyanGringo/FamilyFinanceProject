import logging
import os


def get_logger(name: str = "main"):
    # Проверяем, существует ли логгер с таким именем
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        # Если обработчиков нет, настраиваем логгер
        formatter = logging.Formatter(
            fmt="%(name)s %(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger.setLevel(logging.DEBUG if os.getenv("DEV") else logging.INFO)
        logger.addHandler(handler)
        logger.propagate = False  # Отключаем распространение сообщений к родительским логгерам

    return logger

# TODO: Добавить поддержку 'Должник'
# TODO: При ошибке: log присылать в виде файла
# TODO: Постоянный ключ от Google Cloud
# TODO: Убрать несколько запросов в одном голосовом
# TODO: На основе Apple утечки доработать промпты
# TODO: Сделать в Google Tables "инструкции пользователя для ChatGPT". Пример:
    # Если деньги списаны со счета Влада, то категория всегда ГОСПОДИН
    # Если деньги списаны со счета Лизы, то категория всегда ГОСПОЖА
    # Луна - это собакая Влада и Лизы
# TODO: Корректировка запроса через reply


import logging

from dotenv import load_dotenv

from src import server


# LOGGING


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    # filename="mylog.log",  # TODO: save to file,
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.DEBUG)


# START


if __name__ == "__main__":
    load_dotenv()  # load env from .env
    server.run()

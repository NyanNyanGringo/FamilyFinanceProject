import logging
from src import server
from dotenv import load_dotenv


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        # filename="mylog.log",
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    load_dotenv()  # load env from .env

    server.run()

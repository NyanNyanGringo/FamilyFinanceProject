import logging

import os

from dotenv import load_dotenv

from src import server


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG if os.getenv("DEV") else logging.INFO,
        # filename="mylog.log",
        format="%(name)s %(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    load_dotenv()  # load env from .env

    server.run()
    # from lib.utilities import google_utilities
    #
    # google_utilities.insert_new_row()

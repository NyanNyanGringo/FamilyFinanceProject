import logging

import os

from dotenv import load_dotenv

from lib.utilities.google_utilities import RequestData, ListName

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

    # tests
    # from lib.utilities import google_utilities
    #
    # request_data = RequestData(list_name=ListName.expenses,
    #                            category="Коммуналка Дом",
    #                            account="динары",
    #                            amount=500,
    #                            comment="Test Comment")
    #
    # google_utilities.insert_and_update_row_batch_update(request_data)
    #
    # # TODO: разобраться почему не работает logging и load_dotenv

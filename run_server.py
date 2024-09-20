import logging

import os
import pprint

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

    # server.run()

    # tests 1
    # from lib.utilities.google_utilities import RequestData, ListName
    # from lib.utilities import google_utilities
    #
    # request_data = RequestData(list_name=ListName.expenses,
    #                            expenses_category="Коммуналка Дом",
    #                            account="динары",
    #                            amount=500,
    #                            comment="Test Comment")
    #
    # google_utilities.insert_and_update_row_batch_update(request_data)


    # test 2
    from lib.utilities import openai_utilities
    from lib.utilities import google_utilities

    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.incomes, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.expenses, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.accounts, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.accounts, True))
    # print()
    print(openai_utilities._get_response_format())

    openai_utilities.request_data("800 динар хлеб и молоко")

    # TODO: остановились на том, что google_utilities.get_values возвращает вложенные листы. А также пустые ячейки.
        # Это нужно поправить и после эксперементировать с запросом к ChatGPT API.

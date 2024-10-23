# TODO: меньше запросов в Google Tables
# TODO: log присылать в виде файла
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
logging.getLogger("httpx").setLevel(logging.WARNING)


# START


if __name__ == "__main__":
    load_dotenv()  # load env from .env
    server.run()












    # from dotenv import load_dotenv
    # load_dotenv()
    # import os
    # os.getenv("TELEGRAM_TOKEN")

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
    # from lib.utilities import openai_utilities
    # from lib.utilities import google_utilities
    #
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.incomes, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.expenses, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.accounts, True))
    # print()
    # pprint.pprint(google_utilities.get_values(google_utilities.ConfigRange.accounts, True))
    # print()
    # print(openai_utilities._get_response_format())
    #
    # openai_utilities.request_data("800 динар хлеб и молоко")

    # test 3
    # user_message = "Значит, сделал перевод. Получается, из динары Лиза просто в динары пять тысяч динар. И напиши комментарий, что нужно долг вернуть Лизе."
    #
    # from lib.utilities.openai_utilities import request_data, RequestBuilder, ResponseFormat, MessageRequest
    #
    # request_data(
    #     RequestBuilder(
    #         message_request=MessageRequest(user_message).finance_operation_request_message,
    #         response_format=ResponseFormat().finance_operation_response
    #     )
    # )

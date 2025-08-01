import logging

from openai import OpenAI
import json

from pydantic import BaseModel

from lib.utilities import google_utilities
from lib.utilities.google_utilities import Status, ConfigRange, OperationTypes, Category


# LOGGING


from lib.utilities.log_utilities import get_logger
LOGGER = get_logger(__name__)


# public

CLIENT = OpenAI()


def text2text(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Отправляет текстовый запрос в OpenAI и возвращает ответ.

    Args:
        prompt (str): Текстовый запрос для модели.
        model (str): Название модели OpenAI.

    Returns:
        str: Ответ модели.
    """
    response = CLIENT.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Ты должен ответить только в формате JSON, строго по схеме. Не добавляй никакого текста вне JSON. Если не хватает данных — используй значения по умолчанию, указанные в схеме."},
            {"role": "user", "content": prompt}
        ],
    )

    LOGGER.info(f"{response=}")

    message = response.choices[0].message.content
    return message


def audio2text(audio_path: str, prompt: str = "") -> str:
    """
    Преобразует аудиофайл в текст с помощью OpenAI Whisper.

    Args:
        audio_path (str): Путь к аудиофайлу.
        prompt (str): Контекст для распознавания.

    Returns:
        str: Распознанный текст.
    """
    audio_file = open(audio_path, "rb")

    transcription = CLIENT.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        prompt=prompt
    )

    LOGGER.info(transcription)

    return transcription.text


def audio2text_for_finance(audio_path: str):
    """
    Преобразует аудиофайл в текст с финансовым контекстом для FamilyFinanceProject.

    Args:
        audio_path (str): Путь к аудиофайлу.

    Returns:
        str: Распознанный текст с учётом категорий расходов, доходов и счетов.
    """
    prompt = f"Ты помощник, который транскрибирует запрос пользователя о денежной операции. Используй следующие " \
             f"категории расходов, доходов, а также список счетов для лучшего понимания контекста:\n" \
             f"Категории расходов: {google_utilities.get_values(cell_range=ConfigRange.expenses,transform_to_single_list=True)}" \
             f"Категории доходов: {google_utilities.get_values(cell_range=ConfigRange.incomes, transform_to_single_list=True)}\n" \
             f"Счета: {google_utilities.get_values(cell_range=ConfigRange.accounts, transform_to_single_list=True)}"
    return audio2text(audio_path, prompt=prompt)


# private


def _get_adjustment_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "adjustment_account":
                        {
                            "type": "string",
                            # "description": "Счет корректировки баланса. Если пользователь не назвал, то 'None'.",
                            "strict": True,
                            "items": {
                                "type": "string",
                                "enum": Category.get_accounts()
                            }
                        },
                    "adjustment_amount":
                        {
                            "type": "number",
                            "strict": True,
                            "description": "Сумма корректировки счета."
                                           "Если пользователь говорит выполнить математическую операцию, "
                                           "нужно сложить, вычесть, умножить или разделить суммы в зависимости "
                                           "от его запроса."
                        },
                    "status":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "По-умолчанию статус всегда Committed - то есть корректировка совершена. "
                                           # "Если пользователь каким-то образом сказал, что корректировка "
                                           # "запланирована, то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           # "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            # "description": "Напиши сообщение пользователю: как ты понял его запроси всей ли информации "
                                           # "было достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "adjustment_account",
                    "adjustment_amount",
                    "status",
                    "comment",
                    "final_answer",
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_transfer_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "write_off_account":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Счет списания. Если пользователь не назвал, то None.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_accounts()
                            }
                        },
                    "replenishment_account":
                        {
                            "type": "string",
                            # "description": "Счет пополнения. Если пользователь не назвал, то 'None'.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_accounts()
                            }
                        },
                    "write_off_amount":
                        {
                            "type": "number",
                            "strict": True,
                            "description": "Сумма списания со счета. Сумма должна быть положительная. "
                                           "Если пользователь говорит выполнить математическую операцию, "
                                           "нужно сложить, вычесть, умножить или разделить суммы в зависимости "
                                           "от его запроса."
                        },
                    "replenishment_amount":
                        {
                            "type": "number",
                            "strict": True,
                            "description": "Сумма пополнения счета. Сумма должна быть положительная. "
                                           "Если пользователь говорит выполнить математическую операцию, "
                                           "нужно сложить, вычесть, умножить или разделить суммы в зависимости "
                                           "от его запроса."
                        },
                    "status":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "По-умолчанию статус всегда Committed - то есть перевод совершен. "
                                           # "Если пользователь каким-то образом сказал, что перевод запланирован, "
                                           # "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           # "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            # "description": "Напиши сообщение пользователю: как ты понял его запроси всей ли информации "
                                           # "было достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "write_off_account",
                    "replenishment_account",
                    "write_off_amount",
                    "replenishment_amount",
                    "status",
                    "comment",
                    "final_answer",
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_expenses_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "strict": True,
                "properties": {
                    "expenses_category":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Категория расходов. Если такой категории нет, то категория "
                                           # "'Другое'.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_expenses()
                            }
                        },
                    "account":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Выбери счет расходов. Если такого счета нет в списке, "
                                           # "то счет будет 'None'.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_accounts()
                            }
                        },
                    "amount":
                        {
                            "type": "number",
                            "strict": True,
                            "description": "Сумма, которую потратил пользователь. Сумма должна быть положительная. "
                                           "Если пользователь говорит выполнить математическую операцию, "
                                           "нужно сложить, вычесть, умножить или разделить суммы в зависимости "
                                           "от его запроса."
                        },
                    "status":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "По-умолчанию статус всегда Committed - то есть расход совершен. "
                                           # "Если пользователь каким-то образом сказал, что расход запланирован, "
                                           # "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           # "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            # "description": "Напиши сообщение пользователю: как ты понял его запроси всей ли информации "
                                           # "было достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "expenses_category",
                    "account",
                    "amount",
                    "status",
                    "comment",
                    "final_answer",
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_incomes_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "strict": True,
                "properties": {
                    "incomes_category":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Категория доходов. Если пользователь не назвал категорию доходов, тогда"
                                           # "'None'.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_incomes()
                            }
                        },
                    "account":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Имя счета на который поступили деньги. Если пользователь не назвал счет, "
                                           # "тогда 'None'.",
                            "items": {
                                "type": "string",
                                "enum": Category.get_accounts()
                            }
                        },
                    "amount":
                        {
                            "type": "number",
                            "strict": True,
                            # "description": "Сумма пополнения счета. Сумма должна быть положительная. "
                                           # "Если пользователь не назвал сумму, то сумма равняется -1."
                        },
                    "status":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "По-умолчанию статус всегда Committed - то есть денежка поступила на счет. "
                                           # "Если пользователь каким-то образом сказал, что доход запланирован, "
                                           # "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "strict": True,
                            # "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           # "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            # "description": "Напиши сообщение пользователю: как ты понял его запроси всей ли информации "
                                           # "было достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "incomes_category",
                    "account",
                    "amount",
                    "status",
                    "comment",
                    "final_answer",
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_finance_operation_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "operations":
                        {
                            "type": "array",
                            "items":
                                {
                                    "type": "object",
                                    "properties": {
                                        "user_request_is_relevant":
                                            {
                                                "type": "boolean",

                                            },
                                        "operation_type":
                                            {
                                                "type": "string",
                                                "strict": True,
                                                "description": f"Тип денежной операции. Иначе, None.\n"
                                                               f"Дополнительная информация:\n"
                                                               f"Категории расходов: {Category.get_expenses()}\n"
                                                               f"Категории доходов: {Category.get_incomes()}\n"
                                                               f"Счета: {Category.get_accounts()}\n"
                                                               f"Если сомневаешься между Расходы и Доходы - выбирай "
                                                               f"Расходы.",
                                                "items": {
                                                    "type": "string",
                                                    "enum": ["None"] + OperationTypes.values()
                                                }
                                            },
                                        "source_inputted_text":
                                            {
                                                "type": "string",
                                                "strict": True,
                                                # "description": "Исходное сообщения от пользователя, в которой "
                                                               # "он говорит о данной денежной операции."
                                            },
                                        "message_to_user":
                                            {
                                                "type": "string",
                                                # "description": "Напиши сообщение пользователю: всей ли информации было "
                                                               # "достаточно и является ли запрос релевантным."
                                            },
                                    },
                                    "required": [
                                        "user_request_is_relevant",
                                        "operation_type",
                                        "source_inputted_text",
                                        "message_to_user",
                                    ],
                                    "additionalProperties": False
                                }
                        },
                },
                "required": [
                    "operations",
                ],
                "description": "Важно: внутри одного сообщения от пользователя могут быть несколько операций. Но! Разделить сообщения на несколько можно только в случае, если пользователь явно указывает на разные операции, например, используя 'во-первых', 'во-вторых' и т.д.",
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_finance_operation_message(user_message) -> list:
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message
                }
            ]
        },
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "Ты - связующее звено между пользователем и Google Tables. Твоя задача - точно и "
                            "уверенно определить:\n"
                            "1) Относится ли сообщение пользователя к следующим темам: доходы, расходы, бюджет,"
                            "финансы. Пользователь мог записать сообщения в шутку. Также сообщение может быть "
                            "пустым, содержать неразборчивую речь. Всё это считается нерелевантным запросом.\n"
                            "2) Тип операции. Cмотри на сообщение пользователя и"
                            "категории доходов, расходов и счета - они подскажут тип операции."
                }
            ]
        },
    ]

    return messages


def _get_basic_message(user_message) -> list:
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message
                }
            ]
        },
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "Твоя задача точно и уверенно написать json ответ на основе предварительного анализа "
                            "преобразованного в текст голосового сообщения от пользователя."
                }
            ]
        },
    ]

    return messages


# public


class MessageRequest:
    """
    Класс для формирования сообщений-запросов к OpenAI.
    """
    def __init__(self, user_message):
        self.finance_operation_request_message: list = _get_finance_operation_message(user_message)
        self.basic_request_message: list = _get_basic_message(user_message)


class ResponseFormat:
    """
    Класс для хранения форматов ответов для разных типов операций.
    """
    def __init__(self):
        self.adjustment_response_format: dict = _get_adjustment_response_format()
        self.transfer_response_format: dict = _get_transfer_response_format()
        self.expenses_response_format: dict = _get_expenses_response_format()
        self.incomes_response_format: dict = _get_incomes_response_format()

        self.finance_operation_response: dict = _get_finance_operation_response_format()


class Model:
    """
    Класс с названиями моделей OpenAI.
    """
    gpt_4o_mini: str = "gpt-4o-mini"  # 0.15$
    gpt_4o: str = "gpt-4o"  # 2.50$
    o3_mini: str = "o3-mini"  # 1.10$
    o1: str = "o1"  # 15$
    gpt_4_1: str = "gpt-4.1"  # 2.00$
    gpt_4_1_mini: str = "gpt-4.1-mini"  # 0.40$
    o4_mini: str = "o4-mini"  # 1.10$


class RequestBuilder(BaseModel):
    """
    Дата-класс для построения запроса к OpenAI.

    Args:
        message_request (list): Сообщение-запрос.
        response_format (dict): Формат ответа.
        model (str): Название модели.
    """
    message_request: list  # use MessageRequest().attribute
    response_format: dict  # use ResponseFormat().attribute
    model: str = Model().gpt_4_1  # use Model().attribute


def request_data(request_builder: RequestBuilder) -> dict:
    """
    Отправляет запрос к OpenAI API и возвращает ответ в формате JSON.

    Args:
        request_builder (RequestBuilder): Объект с параметрами запроса к OpenAI.

    Returns:
        dict: Ответ от OpenAI API в формате JSON.

    Note:
        Использует следующие параметры для запроса:
        - temperature: 0.05 (низкая температура для более детерминированных ответов)
        - max_tokens: 2048 (максимальное количество токенов в ответе)
        - top_p: 0.25 (вероятностный порог для генерации)
        - frequency_penalty: 0 (без штрафа за частоту)
        - presence_penalty: 0 (без штрафа за присутствие)
    """
    response = CLIENT.chat.completions.create(
        model=request_builder.model,
        messages=request_builder.message_request,
        response_format=request_builder.response_format,
        temperature=0.05,
        max_tokens=2048,
        top_p=0.25,
        frequency_penalty=0,
        presence_penalty=0,
    )

    LOGGER.info(response)

    message = response.choices[0].message.content

    return json.loads(message)

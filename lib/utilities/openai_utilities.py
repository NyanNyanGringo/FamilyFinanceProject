import logging
import pprint

from openai import OpenAI
import json

from lib.utilities import google_utilities
from lib.utilities.google_utilities import ListName, TransferType, Status, ConfigRange, OperationTypes


def text2text(prompt: str, model: str = "gpt-4o-mini") -> str:
    client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
    )

    logging.info(f"{response=}")

    message = response.choices[0].message.content
    return message


def audio2text(audio_path: str) -> str:
    client = OpenAI()

    audio_file = open(audio_path, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )

    logging.info(transcription)

    return transcription.text


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
                            "description": "Определи счет корректировки баланса. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "adjustment_amount":
                        {
                            "type": "number",
                            "description": "Сумма на которую пользователь скорректировал счет. Если пользователь не "
                                           "назвал сумму, то сумма равняется 0."
                        },
                    "status":
                        {
                            "type": "string",
                            "description": "По-умолчанию статус всегда Committed - то есть корректировка совершена. "
                                           "Если пользователь каким-то образом сказал, что корректировка "
                                           "запланирована, то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": "Напиши как ты понял запрос от пользователя и всей ли информации было "
                                           "достаточно для заполнения json ответа."
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
                            "description": "Определи счет с которого пользователь перевел деньги. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "replenishment_account":
                        {
                            "type": "string",
                            "description": "Определи счет, который пополнил пользователь. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "write_off_amount":
                        {
                            "type": "number",
                            "description": "Сумма, которую пользователь списал со счета. Сумма должна быть "
                                           "положительная. Если пользователь не назвал сумму, то сумма равняется -1."
                        },
                    "replenishment_amount":
                        {
                            "type": "number",
                            "description": "Сумма на которую пользователь пополнил счет. Сумма должна быть "
                                           "положительная. Если пользователь не назвал сумму, то сумма равняется -1."
                        },
                    "status":
                        {
                            "type": "string",
                            "description": "По-умолчанию статус всегда Committed - то есть перевод совершен. "
                                           "Если пользователь каким-то образом сказал, что перевод запланирован, "
                                           "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": "Напиши как ты понял запрос от пользователя и всей ли информации было "
                                           "достаточно для заполнения json ответа."
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
                "properties": {
                    "category":
                        {
                            "type": "string",
                            "description": "Определи категорию расходов. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.expenses,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "account":
                        {
                            "type": "string",
                            "description": "Определи имя счета из которого потратили деньги. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "amount":
                        {
                            "type": "number",
                            "description": "Сумма, которую потратил пользователь. Сумма должна быть положительная. "
                                           "Если пользователь не назвал сумму, то сумма равняется -1."
                        },
                    "status":
                        {
                            "type": "string",
                            "description": "По-умолчанию статус всегда Committed - то есть расход совершен. "
                                           "Если пользователь каким-то образом сказал, что расход запланирован, "
                                           "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": "Напиши как ты понял запрос от пользователя и всей ли информации было "
                                           "достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "category",
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
                "properties": {
                    "category":
                        {
                            "type": "string",
                            "description": "Определи категорию доходов. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.incomes,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "account":
                        {
                            "type": "string",
                            "description": "Определи имя счета на который поступили деньги. Иначе, None.",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(cell_range=ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "amount":
                        {
                            "type": "number",
                            "description": "Сумма пополнения счета. Сумма должна быть положительная. "
                                           "Если пользователь не назвал сумму, то сумма равняется -1."
                        },
                    "status":
                        {
                            "type": "string",
                            "description": "По-умолчанию статус всегда Committed - то есть денежка поступила на счет. "
                                           "Если пользователь каким-то образом сказал, что доход запланирован, "
                                           "то статус Planned.",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "description": "Какой-либо дополнительный комментарий от пользователя. Поле может "
                                           "быть пустым."
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": "Напиши как ты понял запрос от пользователя и всей ли информации было "
                                           "достаточно для заполнения json ответа."
                        }
                },
                "required": [
                    "category",
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


def _get_prebase_response_format() -> dict:
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
                                    "operation_type":
                                        {
                                            "type": "string",
                                            "description": "Определи тип операции: пользователь потратил деньги, "
                                                           "сделал перевод между счетами, скорректировал счет или "
                                                           "получил деньги на счет.",
                                            "items": {
                                                "type": "string",
                                                "enum": OperationTypes.values()
                                            }
                                        },
                                    "operation_text":
                                        {
                                            "type": "string",
                                            "description": "Кусок сообщения от пользователя в оригинальном виде, где"
                                                           "пользователь сообщает о данной операции"
                                        }
                                }
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": "Напиши как ты понял запрос от пользователя и всей ли информации было "
                                           "достаточно для заполнения json ответа."
                        },
                    "user_request_is_correct":
                        {
                            "type": "boolean",
                            "description": "Указывает, является ли запрос пользователя релевантным, корректным и "
                                           "достаточно полным."
                        }
                },
                "required": [
                    "operations",
                    "final_answer"
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def _get_prebase_message(user_message) -> list:
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
                    "text": "Определи тип денежной операции. Внутри одного сообщения от пользователя может "
                            "быть несколько операций - в таком случае внутри листа будет несколько словарей."
                }
            ]
        },
        # {
        #     "role": "assistant",
        #     "content": [
        #         {
        #             "type": "text",
        #             "text": ""
        #         }
        #     ]
        # }
    ]

    return messages


def _get_base_message(user_message) -> list:
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
                    "text": "Твоя задача написать json ответ на основе предварительного анализа "
                            "преобразованного в текст голосового сообщения от пользователя."
                }
            ]
        },
        # {
        #     "role": "assistant",
        #     "content": [
        #         {
        #             "type": "text",
        #             "text": ""
        #         }
        #     ]
        # }
    ]

    return messages

# public


def request_data(user_message: str, model: str = "gpt-4o-mini"):
    client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        messages=_get_base_message(user_message),
        response_format=_get_response_format()
    )

    pprint.pprint(response)
    pprint.pprint(response.choices[0].message.tool_calls[0].function.arguments)
    # message = response.choices[0].message.content
    # return

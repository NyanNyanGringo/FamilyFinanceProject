import logging
import pprint

from openai import OpenAI
import json

from lib.utilities import google_utilities
from lib.utilities.google_utilities import ListName, TransferType, Status, ConfigRange


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


def _get_response_format() -> dict:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "google_tables_response_assistant",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "list_name":
                        {
                            "type": "string",
                            "description": "Это не только название листа в Google Tables, но и "
                                           "вид денежной операции. На основе текста от пользователя "
                                           "нужно определить: он потратил деньги, сделал перевод между "
                                           "счетами или получил деньги.",
                            "items": {
                                "type": "string",
                                "enum": ListName.values()
                            }
                        },
                    "incomes_category":
                        {
                            "type": "string",
                            "description": "Если операция, которую совершил пользователь, относится к доходам, "
                                           "то нужно постараться определить категорию. Иначе, None.",
                            # TODO: остановились тут
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(ConfigRange.incomes,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "expenses_category":
                        {
                            "type": "string",
                            "description": "",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(ConfigRange.expenses,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "transfer_type":
                        {
                            "type": "string",
                            "description": "",
                            "items": {
                                "type": "string",
                                "enum": TransferType.values()
                            }
                        },
                    "account":
                        {
                            "type": "string",
                            "description": "",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "replenishment_account":
                        {
                            "type": "string",
                            "description": "",
                            "items": {
                                "type": "string",
                                "enum": ["None"] + google_utilities.get_values(ConfigRange.accounts,
                                                                               transform_to_single_list=True)
                            }
                        },
                    "amount":
                        {
                            "type": "number",
                            "description": ""
                        },
                    "write_off_amount":
                        {
                            "type": "number",
                            "description": ""
                        },
                    "status":
                        {
                            "type": "string",
                            "description": "",
                            "items": {
                                "type": "string",
                                "enum": Status.values()
                            },
                        },
                    "comment":
                        {
                            "type": "string",
                            "description": ""
                        },
                    "final_answer":
                        {
                            "type": "string",
                            "description": ""
                        }
                },
                "required": [
                    "list_name",
                    "incomes_category",
                    "expenses_category",
                    "transfer_type",
                    "account",
                    "replenishment_account",
                    "amount",
                    "write_off_amount",
                    "status",
                    "comment",
                    "final_answer"
                ],
                "additionalProperties": False
            }
        }
    }

    return response_format


def request_data(user_message: str, model: str = "gpt-4o-mini"):
    client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        messages=[
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
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": ""
                    }
                ]
            }
        ],
        response_format=_get_response_format()
    )
    pprint.pprint(response)
    pprint.pprint(response.choices[0].message.tool_calls[0].function.arguments)
    # message = response.choices[0].message.content
    # return

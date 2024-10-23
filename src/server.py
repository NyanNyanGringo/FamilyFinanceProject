import logging

import os
import time

from functools import partial

import telegram._message
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from lib.utilities.google_utilities import OperationTypes
from lib.utilities.openai_utilities import request_data, RequestBuilder, ResponseFormat, \
    MessageRequest, audio2text_for_finance
from lib.utilities.telegram_utilities import download_voice_message
from lib.utilities.ffmpeg_utilities import convert_oga_to_wav
from lib.utilities.vosk_utilities import audio2text


# LOGGING


logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEV") else logging.INFO,
    format="%(name)s %(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    # filename="mylog.log",  # TODO: save to file
)
LOGGER = logging.getLogger(__name__)


# FUNCTIONS AND CLASSES


class Audio2TextModels:
    whisper = "whisper"
    vosk = "vosk"


def replace_last_string(original_text: str, text_to_add: str):
    texts = original_text.split("\n")
    if len(texts) == 1:
        return text_to_add
    else:
        return "\n".join(texts[:-1] + [text_to_add])


async def get_text_from_audio(update, context, audio2text_model: Audio2TextModels, custom_text: str = None):
    oga_audio_file = await download_voice_message(update, context)
    wav_audio_file = convert_oga_to_wav(oga_audio_file)

    if custom_text:
        text_from_audio = custom_text
    elif audio2text_model == Audio2TextModels.whisper:
        text_from_audio = audio2text_for_finance(wav_audio_file)
    else:
        text_from_audio = audio2text(wav_audio_file)

    return text_from_audio


def format_json_to_telegram_text(json: dict) -> str:
    text = ""
    for key, value in json.items():
        if value:
            text += f"<i>{key}</i>: <b>{value}</b>\n"
    return text.strip()


async def edit_message(message: telegram.Message, text: str, user_message: str = None):
    new_text = ""
    if user_message:
        new_text += f"<code>{user_message}</code>\n\n"
    new_text += text
    await message.edit_text(new_text, parse_mode="HTML")


async def clarify_operation_type(operation_type, processing_message, operation_text):
    try:
        operation_type = OperationTypes.get_item(operation_type)
        return operation_type
    except ValueError:
        await edit_message(message=processing_message,
                           text=f'Тип операции "{operation_type}", который определил ChatGPT, неверный. '
                                f'Попробуйте перезаписать голосовое сообщение.',
                           user_message=operation_text)


def get_reply_keyboard_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Подтвердить", callback_data="confirm"),
            InlineKeyboardButton("Отменить", callback_data="reject")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_response_format_according_to_operation_type(operation_type: str) -> dict:
    if operation_type == OperationTypes.expenses:
        return ResponseFormat().expenses_response_format
    elif operation_type == OperationTypes.incomes:
        return ResponseFormat().incomes_response_format
    elif operation_type == OperationTypes.transfers:
        return ResponseFormat().transfer_response_format
    elif operation_type == OperationTypes.adjustment:
        return ResponseFormat().adjustment_response_format

    raise ValueError(f"Operation type {operation_type} not supported.")

# HANDLES


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

    # send message to user about error
    if isinstance(update, Update) and update.message:
        try:
            # Пытаемся отправить пользователю сообщение об ошибке
            await update.message.reply_text("Произошла ошибка при обработке вашего запроса. "
                                            "Пожалуйста, попробуйте позже.")
        except Exception as e:
            LOGGER.error(f"Ошибка при отправке сообщения пользователю: {e}")


async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # confirm button click

    operation_type = context.user_data["operation_type"]
    request_message = context.user_data["request_message"]
    # context.user_data["confirm"]  # STOPPED THERE :)
    # context.user_data["reject"]

    LOGGER.info(f"{operation_type=}")
    LOGGER.info(f"{request_message=}")
    LOGGER.info(f"{context.user_data['confirm']=}")
    LOGGER.info(f"{context.user_data['reject']=}")

    # remove buttons
    await query.edit_message_reply_markup(reply_markup=None)


async def voice_message_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        audio2text_model: Audio2TextModels = Audio2TextModels.whisper,
        custom_text: str = None) -> None:

    # Step I. Convert voice message to text.
    processing_message = await update.message.reply_text("1/3 Конвертирую аудио в текст. Ожидайте...")
    text_from_audio = await get_text_from_audio(update, context, audio2text_model, custom_text)

    # Step II. First request to ChatGPT: get json data with operation type and text validity.
    # Text will be divided into parts if user ask for few request in one voice message.
    await edit_message(message=processing_message,
                       text="2/3 Определяю тип операции и валидность текста. Ожидайте...",
                       user_message=text_from_audio)
    finance_operation_request_message = request_data(
        RequestBuilder(
            message_request=MessageRequest(user_message=text_from_audio).finance_operation_request_message,
            response_format=ResponseFormat().finance_operation_response
        )
    )

    # Step III. Second requests to ChatGPT: get json data that will be added to Google Tables.
    for _, finance_operations in finance_operation_request_message.items():
        for finance_operation in finance_operations:

            operation_type: str = finance_operation.get("operation_type")
            operation_text: str = finance_operation.get("operation_text")
            message_to_user: str = finance_operation.get("message_to_user")
            user_request_is_correct: bool = finance_operation.get("user_request_is_relevant")

            operation_type = await clarify_operation_type(operation_type, processing_message, operation_text)
            if not operation_type:
                continue

            if not user_request_is_correct:
                await edit_message(message=processing_message,
                                   text=f'Запрос некорректен. Ответ ChatGPT: "{message_to_user}"',
                                   user_message=operation_text)
                continue

            await edit_message(message=processing_message,
                               text=f"3/3 Определяю данные для Google Tables. Ожидайте...",
                               user_message=operation_text)

            request_message = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=operation_text).basic_request_message,
                    response_format=get_response_format_according_to_operation_type(operation_type))
            )

            # save operation_type and request_message to use in button_click_handler()
            context.user_data["operation_type"] = operation_type
            context.user_data["request_message"] = request_message

            # send message with buttons
            await processing_message.edit_text(format_json_to_telegram_text(request_message),
                                               reply_markup=get_reply_keyboard_markup(),
                                               parse_mode="HTML")


def run() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Устанавливаем глобальный обработчик ошибок
    application.add_error_handler(global_error_handler)

    # Используем functools.partial для передачи дополнительного аргумента
    handler_with_args = partial(
        voice_message_handler,
        audio2text_model=Audio2TextModels.whisper,
        custom_text="2238 динары продукты"
    )

    # Привязываем обработчики для разных моделей
    application.add_handler(
        MessageHandler(
            filters.VOICE & ~filters.COMMAND,
            handler_with_args
        )
    )

    # Обработчик для нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button_click_handler))

    # run
    application.run_polling(allowed_updates=Update.ALL_TYPES)

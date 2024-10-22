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


class Audio2TextModels:
    whisper = "whisper"
    vosk = "vosk"


def replace_last_string(original_text: str, text_to_add: str):
    texts = original_text.split("\n")
    if len(texts) == 1:
        return text_to_add
    else:
        return "\n".join(texts[:-1] + [text_to_add])


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # Сохраняем выбор пользователя в context.user_data
    if query.data == "yes":
        context.user_data["user_choice"] = True
    elif query.data == "no":
        context.user_data["user_choice"] = False

    # Вы можете оставить текст сообщения без изменений, если это нужно
    await query.edit_message_reply_markup(reply_markup=None)  # Убираем кнопки, но текст остаётся прежним


def get_text_from_audio(audio2text_model: Audio2TextModels, wav_audio_file: str, custom_text: str = None):
    if custom_text:
        text_from_audio = custom_text
    elif audio2text_model == Audio2TextModels.whisper:
        text_from_audio = audio2text_for_finance(wav_audio_file)
    else:
        text_from_audio = get_text_from_audio(wav_audio_file)

    return text_from_audio


def format_json_to_telegram_text(json: dict) -> str:
    text = ""
    for key, value in json.items():
        if value:
            text += f"<i>{key}</i>: <b>{value}</b>\n"
    return text.strip()


async def add_row_to_google_tables_based_on_the_voice_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        audio2text_model: Audio2TextModels = Audio2TextModels.whisper,
        custom_text: str = None) -> None:
    """
    1. Принимает update от Telegram в момент отправки пользователем голосового сообщения;
    2. Сохраняет голосовое сообщение в папку voice_messages в формате .oga;
    3. Конвертирует в формат .wav;
    4. Переводит .wav в текст (через whisper или vosk)
    5.
    """
    async def edit_message(message: telegram.Message, text: str, user_message: str = None):
        new_text = ""
        if user_message:
            new_text += f"<code>{user_message}</code>\n\n"
        new_text += text
        await message.edit_text(new_text, parse_mode="HTML")

    # audio to text
    processing_message = await update.message.reply_text("1/3 Конвертирую аудио в текст. Ожидайте...")
    oga_audio_file = await download_voice_message(update, context)
    wav_audio_file = convert_oga_to_wav(oga_audio_file)
    text_from_audio = get_text_from_audio(audio2text_model, wav_audio_file, custom_text)

    await edit_message(message=processing_message,
                       text="2/3 Определяю тип операции и валидность текста. Ожидайте...",
                       user_message=text_from_audio)
    finance_operation_request_message = request_data(
        RequestBuilder(
            message_request=MessageRequest(user_message=text_from_audio).finance_operation_request_message,
            response_format=ResponseFormat().finance_operation_response
        )
    )

    # get json data for google tables
    for _, finance_operations in finance_operation_request_message.items():
        for i, finance_operation in enumerate(finance_operations):

            operation_type: str = finance_operation.get("operation_type")
            operation_text: str = finance_operation.get("operation_text")
            message_to_user: str = finance_operation.get("message_to_user")
            user_request_is_correct: bool = finance_operation.get("user_request_is_relevant")

            if not user_request_is_correct:
                await edit_message(message=processing_message,
                                   text=f'Запрос некорректен. Ответ ChatGPT: "{message_to_user}"',
                                   user_message=operation_text)
                continue

            await edit_message(message=processing_message,
                               text=f"3/3 Определяю данные для Google Tables. Ожидайте...",
                               user_message=operation_text)

            operation_type = OperationTypes.get_item(operation_type)

            keyboard = [
                [InlineKeyboardButton("Подтвердить", callback_data="yes"),
                 InlineKeyboardButton("Удалить", callback_data="no")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if operation_type == OperationTypes.expenses:

                request_message = request_data(
                    RequestBuilder(
                        message_request=MessageRequest(
                            user_message=operation_text).basic_request_message,
                        response_format=ResponseFormat().expenses_response_format
                    )
                )

                # Отправляем сообщение с кнопками
                message = format_json_to_telegram_text(request_message)
                await processing_message.edit_text(message,
                                                   reply_markup=reply_markup,
                                                   parse_mode="HTML")

            # elif operation_type == OperationTypes.incomes:
            #
            #     request_message = request_data(
            #         RequestBuilder(
            #             message_request=MessageRequest(
            #                 user_message=operation_text).basic_request_message,
            #             response_format=ResponseFormat().incomes_response_format
            #         )
            #     )
            #
            #     final_message = replace_last_string(final_message, f"\nДанные Google Tables: {request_message}")
            #     await processing_message.edit_text(final_message)
            #
            # elif operation_type == OperationTypes.transfers:
            #
            #     request_message = request_data(
            #         RequestBuilder(
            #             message_request=MessageRequest(
            #                 user_message=operation_text).basic_request_message,
            #             response_format=ResponseFormat().transfer_response_format
            #         )
            #     )
            #
            #     final_message = replace_last_string(final_message, f"\nДанные Google Tables: {request_message}")
            #     await processing_message.edit_text(final_message)
            #
            # elif operation_type == OperationTypes.adjustment:
            #
            #     request_message = request_data(
            #         RequestBuilder(
            #             message_request=MessageRequest(
            #                 user_message=operation_text).basic_request_message,
            #             response_format=ResponseFormat().adjustment_response_format
            #         )
            #     )
            #
            #     final_message = replace_last_string(final_message, f"\nДанные Google Tables: {request_message}")
            #     await processing_message.edit_text(final_message)

    # await processing_message.edit_text(final_message)


def run() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Используем functools.partial для передачи дополнительного аргумента
    handler_with_args = partial(
        add_row_to_google_tables_based_on_the_voice_message,
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
    # application.add_handler(CallbackQueryHandler(handle_button_click))

    # run
    application.run_polling(allowed_updates=Update.ALL_TYPES)

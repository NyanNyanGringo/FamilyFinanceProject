import logging

import os

from functools import partial

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from lib.utilities.openai_utilities import text2text, audio2text
from lib.utilities.telegram_utilities import download_voice_message
from lib.utilities.ffmpeg_utilities import convert_oga_to_wav
from lib.utilities.vosk_utilities import get_text_from_audio


class Audio2TextModels:
    whisper = "whisper"
    vosk = "vosk"


async def add_row_to_google_tables_based_on_the_voice_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        audio2text_model: Audio2TextModels = Audio2TextModels.vosk) -> None:
    """
    1. Принимает update от Telegram в момент отправки пользователем голосового сообщения;
    2. Сохраняет голосовое сообщение в папку voice_messages в формате .oga;
    3. Конвертирует в формат .wav;
    4. Переводит .wav в текст (через whisper или vosk)
    5. TODO:
    """
    processing_message = await update.message.reply_text("Конвертирую аудио в текст. Ожидайте...")

    oga_audio_file = await download_voice_message(update, context)
    wav_audio_file = convert_oga_to_wav(oga_audio_file)

    if audio2text_model == Audio2TextModels.whisper:
        raw_text = audio2text(wav_audio_file)
    else:
        raw_text = get_text_from_audio(wav_audio_file)

    if not raw_text.strip():
        await processing_message.edit_text("Не удалось распознать текст.")

    corrected_text = text2text(f"Расставь знаки препинания, исправь грамматические ошибки и структурируй текст. "
                               f"Текст: {raw_text}")

    final_message = f"Текст из аудио-файла:\n\n{raw_text}\n\nФинальный текст:\n\n{corrected_text}"
    await processing_message.edit_text(final_message)


def run() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Используем functools.partial для передачи дополнительного аргумента
    handler_with_vosk = partial(
        add_row_to_google_tables_based_on_the_voice_message,
        audio2text_model=Audio2TextModels.vosk
    )

    # Привязываем обработчики для разных моделей
    application.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, handler_with_vosk))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

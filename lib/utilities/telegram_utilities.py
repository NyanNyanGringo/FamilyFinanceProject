import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from lib.utilities.os_utilities import get_voice_messages_path


async def download_voice_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Downloads Telegram voice message to the voice_messages folder in .oga format
    :
    :return: path to downloaded voice message
    """
    file_id = update.message.voice.file_id
    voice_message = await context.bot.get_file(file_id)

    current_time: str = datetime.now().strftime("%Y%m%d_%H-%M-%S_%f")
    voice_message_path = os.path.join(get_voice_messages_path(create=True),
                                      "voice_message_" + current_time + ".oga")

    await voice_message.download_to_drive(voice_message_path)

    return voice_message_path

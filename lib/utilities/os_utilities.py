import os
from datetime import datetime
import enum
import platform

from config import VOSK_MODEL


# public


def get_voice_messages_path(create: bool = False) -> str:
    """
    Возвращает путь к папке с голосовыми сообщениями. Создаёт папку при необходимости.

    Args:
        create (bool): Создать папку, если не существует.

    Returns:
        str: Путь к папке voice_messages.
    """
    voice_messages_path = os.path.join(_get_root_path(), "voice_messages")

    if create:
        os.makedirs(voice_messages_path, exist_ok=True)

    return voice_messages_path


def get_ffmpeg_executable_path() -> str:
    """
    Возвращает путь к исполняемому файлу ffmpeg в зависимости от ОС.

    Returns:
        str: Путь к ffmpeg.
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # On macOS, ffmpeg is likely installed via Homebrew and available in PATH
        return "ffmpeg"
    elif system == "Windows":
        # On Windows, use the local ffmpeg executable
        return os.path.join(_get_root_path(), "ffmpeg", "bin", "ffmpeg.exe")
    else:  # Linux or other systems
        # On Linux, assume ffmpeg is in PATH
        return "ffmpeg"


def get_vosk_model_path() -> str:
    """
    Возвращает путь к модели Vosk. Бросает ошибку, если модель не найдена.

    Returns:
        str: Путь к модели Vosk.
    """
    vosk_model_path = os.path.join(_get_root_path(), "models", VOSK_MODEL)

    if not os.path.exists(vosk_model_path):
        raise FileNotFoundError(f"Модель не найдена: {vosk_model_path}")

    return vosk_model_path


# private


def _get_root_path() -> str:
    """
    Возвращает корневой путь проекта.

    Returns:
        str: Абсолютный путь к корню проекта.
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

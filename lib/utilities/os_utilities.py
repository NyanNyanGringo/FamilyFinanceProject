import os
from config import VOSK_MODEL


# public


def get_voice_messages_path(create: bool = False) -> str:
    voice_messages_path = os.path.join(_get_root_path(), "voice_messages")

    if create:
        os.makedirs(voice_messages_path, exist_ok=True)

    return voice_messages_path


def get_ffmpeg_executable_path() -> str:
    return os.path.join(_get_root_path(), "ffmpeg", "bin", "ffmpeg.exe")


def get_vosk_model_path() -> str:
    vosk_model_path = os.path.join(_get_root_path(), "models", VOSK_MODEL)

    if not os.path.exists(vosk_model_path):
        raise FileNotFoundError(f"Модель не найдена: {vosk_model_path}")

    return vosk_model_path


# private


def _get_root_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

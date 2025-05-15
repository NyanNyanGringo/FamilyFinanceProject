import os
import enum
import platform

from config import VOSK_MODEL


# public


def get_voice_messages_path(create: bool = False) -> str:
    voice_messages_path = os.path.join(_get_root_path(), "voice_messages")

    if create:
        os.makedirs(voice_messages_path, exist_ok=True)

    return voice_messages_path


def get_ffmpeg_executable_path() -> str:
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
    vosk_model_path = os.path.join(_get_root_path(), "models", VOSK_MODEL)

    if not os.path.exists(vosk_model_path):
        raise FileNotFoundError(f"Модель не найдена: {vosk_model_path}")

    return vosk_model_path


class GoogleAuthType(enum.Enum):
    CREDENTIALS = "credentials.json"
    TOKEN = "token.json"


def get_google_filepath(auth_type: GoogleAuthType) -> str:
    return os.path.join(_get_root_path(), "google_credentials", auth_type.value)


# private


def _get_root_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

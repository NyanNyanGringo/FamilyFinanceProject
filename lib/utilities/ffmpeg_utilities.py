import os
import subprocess

from lib.utilities.os_utilities import get_ffmpeg_executable_path


def convert_oga_to_wav(input_file: str) -> str:
    """
    :return: path to .wav file
    """
    output_path = os.path.splitext(input_file)[0] + ".wav"

    try:
        command = [
            get_ffmpeg_executable_path(),
            '-i', input_file,
            '-ar', '16000',  # Установка частоты дискретизации 16 кГц
            '-ac', '1',  # Установка моно канала
            output_path
        ]

        subprocess.run(command, check=True)
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при конвертации: {e}")

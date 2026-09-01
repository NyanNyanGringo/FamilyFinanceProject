import os
import subprocess

from lib.utilities.os_utilities import get_ffmpeg_executable_path


def get_wav_output_path(input_file: str) -> str:
    return os.path.splitext(input_file)[0] + ".wav"


def convert_oga_to_wav(input_file: str) -> str:
    """
    :return: path to .wav file
    """
    output_path = get_wav_output_path(input_file)

    command = [
        get_ffmpeg_executable_path(),
        "-y",
        "-i",
        input_file,
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]

    subprocess.run(command, check=True)
    return output_path

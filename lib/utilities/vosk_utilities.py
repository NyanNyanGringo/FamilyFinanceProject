import logging

import wave
import json

from vosk import Model, KaldiRecognizer

from lib.utilities.os_utilities import get_vosk_model_path


# LOGGING


from lib.utilities.log_utilities import get_logger
LOGGER = get_logger(__name__)


def audio2text(wav_audio_file: str, frames: int = 4000) -> str:
    """
    Преобразует аудиофайл в текст с помощью модели Vosk.

    Args:
        wav_audio_file (str): Путь к WAV аудиофайлу.
        frames (int, optional): Количество кадров для чтения за раз. По умолчанию 4000.

    Returns:
        str: Распознанный текст из аудиофайла.
    """
    model = Model(get_vosk_model_path())
    wf = wave.open(wav_audio_file, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())

    final_result = ""

    while True:
        data = wf.readframes(frames)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = rec.Result()
            text = json.loads(result)["text"]
            final_result += text + " "
        else:  # TODO: add logger
            partial_result = rec.PartialResult()

    final_result += json.loads(rec.FinalResult())["text"]

    LOGGER.info(final_result)

    return final_result

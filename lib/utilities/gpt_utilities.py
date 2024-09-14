import logging

from openai import OpenAI


def text2text(prompt: str, model: str = "gpt-4o-mini") -> str:

    client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
    )

    logging.info(f"{response=}")

    message = response.choices[0].message.content
    return message


def audio2text(audio_path: str) -> str:
    client = OpenAI()

    audio_file = open(audio_path, "rb")
    transcription = client.audio.transcriptions.create(
      model="whisper-1",
      file=audio_file,
    )

    logging.info(transcription)

    return transcription.text

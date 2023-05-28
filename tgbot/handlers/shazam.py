import io

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType
from pydub import AudioSegment
from shazamio import Shazam

from tgbot.handlers.user import run_blocking_io


async def shazam_start_func(message: types.Message, state):
    await state.reset_state()
    await message.answer("Отправь мне голосовое сообщение, а я постараюсь узнать трек")


async def shazam_get_voice_message(message: types.Message):
    shazam = Shazam()
    voice_file = io.BytesIO()
    await message.voice.download(destination_file=voice_file)
    audio_segment = await run_blocking_io(AudioSegment.from_file, voice_file, "ogg")
    data = await shazam.recognize_song(audio_segment)
    song = data.get("track")
    if not song:
        await message.answer("Я не смог распознать песню")
        return
    await message.answer(f"{song['subtitle']} - {song['title']}\n"
                         f"Больше музыки на @jammy_music_bot")


def register_shazam(dp: Dispatcher):
    dp.register_message_handler(shazam_get_voice_message, content_types=ContentType.VOICE)

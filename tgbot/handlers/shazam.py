import io

from aiogram import types, Dispatcher
from aiogram.types import ContentType, InputFile
import aiogram.utils.markdown as fmt
from pydub import AudioSegment
from shazamio import Shazam
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch

from tgbot.keyboards.inline import music_msg_keyboard
from tgbot.misc.exceptions import FileIsTooLarge
from tgbot.misc.misc_funcs import get_audio_file_from_yt_video, run_blocking_io, run_cpu_bound, \
    filter_songs_without_correct_duration


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

    try:
        text = fmt.text(f"{song['subtitle']} - {song['title']}")
    except KeyError:
        await message.answer("Я не смог распознать песню")
        return
    await message.answer(f"Это {fmt.hcode(text)}")

    video_searcher = await run_blocking_io(VideosSearch, text, 1, 'ru-RU', 'RU')
    search_results = await run_cpu_bound(filter_songs_without_correct_duration, video_searcher)
    if not search_results:
        return
    video_id = search_results[0]["id"]
    if not video_id:
        return
    yt_link = f"https://music.youtube.com/watch?v={video_id}"
    try:
        yt_video = YouTube(yt_link, use_oauth=True)
    except Exception:
        yt_link = f"https://www.youtube.com/watch?v={video_id}"
        yt_video = YouTube(yt_link, use_oauth=True)
    if not yt_video:
        return
    try:
        audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
    except (AgeRestrictedError, FileIsTooLarge):
        return
    await message.answer_audio(InputFile(audio_file), title=audio_stream.title,
                               performer=yt_video.author if yt_video.author else None,
                               reply_markup=music_msg_keyboard, caption='Больше музыки на @jammy_music_bot')


def register_shazam(dp: Dispatcher):
    dp.register_message_handler(shazam_get_voice_message, state="*", content_types=ContentType.VOICE)

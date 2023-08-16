from aiogram import types, Dispatcher
import lyricsgenius

import aiogram.utils.markdown as fmt
from tgbot.config import Config
from tgbot.keyboards.inline import music_msg_keyboard
from tgbot.misc.exceptions import FileIsTooLarge
from tgbot.misc.misc_funcs import get_audio_file_from_yt_video, run_blocking_io
from tgbot.misc.states import JammyMusicStates

from ytmusicapi import YTMusic
from pytube import YouTube

from aiogram.types import ContentType, InputFile
from pytube.exceptions import AgeRestrictedError


async def find_song_by_words(message: types.Message):
    await JammyMusicStates.find_music_by_words.set()
    await message.answer("Отправь часть текста песни, а я отправлю ее название, если найду")


async def format_songs_title_to_message_text(data):
    msg_text = f"{fmt.hbold('Результаты по вашему запросу:')}\n"
    for item in data:
        try:
            artist_names = item['result']['artist_names']
            song_title = item['result']['title_with_featured']
            msg_text += f"{fmt.hcode(artist_names + ' ' + song_title)}\n"
        except KeyError:
            continue
    return msg_text


async def get_text_to_find_song(message: types.Message, config: Config, state):
    await state.reset_state()
    lyrics_genius = lyricsgenius.Genius(config.tg_bot.genius_token)
    msg_text = fmt.text(message.text)
    result = lyrics_genius.search_lyrics(msg_text, per_page=3)
    if not result:
        await message.answer("К сожалению, мне не удалось найти данную песню")
        return
    else:
        try:
            songs = result["sections"][0]["hits"]
            if not songs:
                raise KeyError
        except KeyError:
            await message.answer("К сожалению, мне не удалось найти данную песню")
            return
    msg_text = await format_songs_title_to_message_text(songs)
    await message.answer(msg_text)

    try:
        first_song = songs[0]
        yt: YTMusic = YTMusic("./oauth.json")
        search_results = (await run_blocking_io(yt.search, first_song["result"]["full_title"], "songs", None, 1))[0]
    except (IndexError, ValueError):
        return
    if not search_results:
        return
    video_id = search_results.get("videoId")
    if not video_id:
        return
    yt_link = f"https://music.youtube.com/watch?v={video_id}"
    try:
        yt_video = YouTube(yt_link)
    except Exception:
        yt_link = f"https://www.youtube.com/watch?v={video_id}"
        yt_video = YouTube(yt_link)
    if not yt_video:
        return
    try:
        audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
    except AgeRestrictedError:
        return
    except FileIsTooLarge:
        return
    await message.answer_audio(InputFile(audio_file), title=audio_stream.title,
                               performer=yt_video.author if yt_video.author else None,
                               reply_markup=music_msg_keyboard, caption='Больше музыки на @jammy_music_bot')


async def get_unknown_content_to_find_song(message: types.Message):
    await message.answer("Похоже, что вы хотели найти песню по тексту, но мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")


def register_find_song_by_words(dp: Dispatcher):
    dp.register_message_handler(get_text_to_find_song, content_types=ContentType.TEXT,
                                state=JammyMusicStates.find_music_by_words)
    dp.register_message_handler(get_unknown_content_to_find_song, content_types=ContentType.ANY,
                                state=JammyMusicStates.find_music_by_words)

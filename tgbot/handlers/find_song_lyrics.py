import logging
import re
from math import ceil

from aiogram import types, Dispatcher
from aiogram.types import ContentType
from lyricsgenius.song import Song
from ytmusicapi import YTMusic

from tgbot.handlers.user import run_cpu_bound
from tgbot.misc.states import JammyMusicStates
from tgbot.config import Config
import lyricsgenius


async def find_lyrics(message: types.Message):
    await JammyMusicStates.find_lyrics.set()
    await message.answer("Отправь мне название трека и я верну тебе текст песни, если найду")


def remove_pattern_from_string(text, pattern):
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text


async def get_lyrics(message: types.Message, config: Config, state):
    await state.reset_state()
    try:
        tracks: list[dict] = YTMusic().search(query=message.text, filter="songs", limit=1)
        if not tracks:
            song_title = message.text
            song_artists = ""
        else:
            track = tracks[0]
            song_title = track["title"]
            song_artists = ", ".join([artist.get("name") for artist in track.get("artists")])
        lyrics_genius = lyricsgenius.Genius(config.tg_bot.genius_token)
        result: Song = lyrics_genius.search_song(title=song_title, artist=song_artists if song_artists else "")
        if not result:
            song_title = message.text
            song_artists = ""
            result: Song = lyrics_genius.search_song(title=song_title, artist=song_artists if song_artists else "")
            if not result:
                await message.answer("Песня не было найдена")
                return
        # song_text = result.lyrics[result.lyrics.find("\n"):]
        try:
            # song_text = result.lyrics[result.lyrics.find("Contributors") + 12:]
            # await message.answer(song_text)
            song_text = result.lyrics
            lyrics_start_index = song_text.find('Lyrics')
            if lyrics_start_index != -1:
                song_text = f"{song_text[lyrics_start_index + 6:]}"
            song_text = await run_cpu_bound(remove_pattern_from_string, song_text, r'\d*Embed$')
        except:
            song_text = result.lyrics
            logging.info(f"Ошибка обрезки текста песни msg.text: \n{message.text}")
        if len(song_text) > 4095:
            for num_of_msgs in range(ceil(len(song_text) / 4096)):
                first_index = num_of_msgs * 4096
                await message.answer(song_text[first_index: first_index + 4096])
        else:
            await message.answer(song_text)
    except Exception as exc:
        await message.answer("К сожалению, нам не удалось найти текст данной песни")
        raise exc


async def get_unknown_content_to_find_lyrics(message: types.Message):
    await message.answer("Похоже, что вы хотели найти текст песни, но мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")
                         

def register_find_lyrics(dp: Dispatcher):
    dp.register_message_handler(get_lyrics, content_types=ContentType.TEXT,
                                state=JammyMusicStates.find_lyrics)
    dp.register_message_handler(get_unknown_content_to_find_lyrics, content_types=ContentType.ANY,
                                state=JammyMusicStates.find_lyrics)

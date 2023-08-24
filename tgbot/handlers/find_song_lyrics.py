import logging
import re
from math import ceil

from aiogram import types, Dispatcher
from aiogram.types import ContentType
import aiogram.utils.markdown as fmt
from lyricsgenius.song import Song
from youtubesearchpython import VideosSearch

from tgbot.misc.misc_funcs import run_cpu_bound, filter_songs_without_correct_duration
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
    msg_text = fmt.text(message.text)
    try:
        # TODO SYNC FUNC
        tracks_json = VideosSearch(msg_text, 1, 'ru-RU', 'RU')
        tracks = tracks_json.result()
        print(tracks)
        #  tracks: list[dict] = yt_music.search(query=msg_text, filter="songs", limit=1)
        if not tracks:
            song_title = msg_text
            song_artists = ""
        else:
            track = tracks["result"][0]
            print(track)
            song_title = fmt.text(track["title"])
            print(song_title)
            #  song_artists = fmt.text(", ".join([artist.get("name") for artist in track.get("artists")]))
        lyrics_genius = lyricsgenius.Genius(config.tg_bot.genius_token)
        result: Song = lyrics_genius.search_song(song_title, get_full_info=False)  # работает
        if not result:
            song_title = msg_text
            song_artists = ""
            result: Song = lyrics_genius.search_song(title=song_title, artist=song_artists)
            if not result:
                await message.answer("Мне не удалось найти песню")
                return
        # song_text = result.lyrics[result.lyrics.find("\n"):]
        try:
            # song_text = result.lyrics[result.lyrics.find("Contributors") + 12:]
            # await message.answer(song_text)
            song_text = fmt.text(result.lyrics)
            lyrics_start_index = song_text.find('Lyrics')
            if lyrics_start_index != -1:
                song_text = f"{song_text[lyrics_start_index + 6:]}"
            song_text = await run_cpu_bound(remove_pattern_from_string, song_text, r'\d*Embed$')
        except Exception:
            song_text = result.lyrics
            logging.info(f"Ошибка обрезки текста песни msg.text: \n{msg_text}")
        if len(song_text) > 4095:
            for num_of_msgs in range(ceil(len(song_text) / 4096)):
                first_index = num_of_msgs * 4096
                await message.answer(f"{fmt.hcode(song_text[first_index: first_index + 4096])}")
        else:
            await message.answer(f"{fmt.hcode(song_text)}")
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

from math import ceil

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType

from tgbot.misc.exceptions import SongNotFound
from tgbot.misc.states import JammyMusicStates
from tgbot.config import Config
import lyricsgenius


async def find_lyrics(message: types.Message):
    await JammyMusicStates.find_lyrics.set()
    await message.answer("Отправь мне название трека и я верну тебе текст песни, если найду")


async def get_lyrics(message: types.Message, config: Config, state):
    await state.reset_state()
    try:
        lyrics_genius = lyricsgenius.Genius(config.tg_bot.genius_token)
        result = lyrics_genius.search_song(message.text)
        if not result:
            raise SongNotFound
        song_text = result.lyrics
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
    dp.register_message_handler(find_lyrics, Text("📄 Найти текст песни"),
                                state="*")
    dp.register_message_handler(get_lyrics, content_types=ContentType.TEXT,
                                state=JammyMusicStates.find_lyrics)
    dp.register_message_handler(get_unknown_content_to_find_lyrics, content_types=ContentType.ANY,
                                state=JammyMusicStates.find_lyrics)

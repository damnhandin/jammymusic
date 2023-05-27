from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType

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
        m = result.lyrics
        if len(m) > 4095:
            for x in range(0, len(m), 4095):
                await message.answer(m[x:x + 4095])
        else:
            await message.answer(result.lyrics)
    except Exception:
        await message.answer("К сожалению, нам не удалось найти текст данной песни")


async def get_unknown_content_to_find_lyrics(message: types.Message):
    await message.answer("Похоже, что вы хотели найти текст песни, но мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")

def register_find_lyrics(dp: Dispatcher):
    dp.register_message_handler(find_lyrics, Text("📄 Найти текст песни"))
    dp.register_message_handler(get_lyrics, content_types=ContentType.TEXT,
                                state=JammyMusicStates.find_lyrics)
    dp.register_message_handler(get_unknown_content_to_find_lyrics, content_types=ContentType.ANY,
                                state=JammyMusicStates.find_lyrics)

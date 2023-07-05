from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType
import lyricsgenius

from tgbot.config import Config
from tgbot.misc.states import JammyMusicStates


async def find_song_by_words(message: types.Message):
    await JammyMusicStates.find_music_by_words.set()
    await message.answer("Отправь часть текста песни, а я отправлю ее название, если найду")


async def format_songs_title_to_message_text(data):
    msg_text = "<b>Результаты по вашему запросу:</b>\n"
    for item in data:
        try:
            msg_text += f"{(item['result']['artist_names']).lstrip()} - {item['result']['title_with_featured']}\n"
        except KeyError:
            continue
    return msg_text


async def get_text_to_find_song(message: types.Message, config: Config, state):
    await state.reset_state()
    lyrics_genius = lyricsgenius.Genius(config.tg_bot.genius_token)
    result = lyrics_genius.search_lyrics(message.text, per_page=3)
    if not result:
        await message.answer("К сожалению, нам не удалось найти данную песню")
        return
    else:
        try:
            result = result["sections"][0]["hits"]
        except KeyError:
            await message.answer("К сожалению, нам не удалось найти данную песню")
            return
    msg_text = await format_songs_title_to_message_text(result)
    await message.answer(msg_text)


async def get_unknown_content_to_find_song(message: types.Message):
    await message.answer("Похоже, что вы хотели найти песню по тексту, но мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")


def register_find_song_by_words(dp: Dispatcher):
    dp.register_message_handler(get_text_to_find_song, content_types=ContentType.TEXT,
                                state=JammyMusicStates.find_music_by_words)
    dp.register_message_handler(get_unknown_content_to_find_song, content_types=ContentType.ANY,
                                state=JammyMusicStates.find_music_by_words)

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text


async def find_song_words(message: types.Message):
    pass


def register_find_song_words(dp: Dispatcher):
    dp.register_message_handler(find_song_words, Text("🎵 Найти песню по словам"))

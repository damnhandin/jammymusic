from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text


async def find_song_lyrics(message: types.Message):
    pass


def register_find_lyrics(dp: Dispatcher):
    dp.register_message_handler(find_song_lyrics, Text("📄 Найти текст песни"))

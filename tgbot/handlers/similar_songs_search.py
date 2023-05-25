from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text


async def similar_songs_search(message: types.Message):
    pass


def register_similar_songs_search(dp: Dispatcher):
    dp.register_message_handler(similar_songs_search, Text("🎼 Найти похожие треки"))

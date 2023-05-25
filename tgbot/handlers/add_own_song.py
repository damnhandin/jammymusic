from aiogram import Dispatcher
from aiogram.dispatcher.filters import Text


async def add_own_music_func(message):
    pass


def register_add_own_music(dp: Dispatcher):
    dp.register_message_handler(add_own_music_func, Text("😎 Добавить свой трек"))


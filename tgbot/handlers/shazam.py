from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text


async def shazam(message: types.Message):
    pass


def register_shazam(dp: Dispatcher):
    dp.register_message_handler(shazam, Text("🎙 Shazam"))

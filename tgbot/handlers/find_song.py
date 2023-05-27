from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text


async def find_song_func(message: types.Message):
    await message.answer("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио")


def register_find_song(dp: Dispatcher):
    dp.register_message_handler(find_song_func, Text("🔍 Найти музыку"),
                                state="*")

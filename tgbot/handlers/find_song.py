from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text


async def find_song_func(message: types.Message, state: FSMContext):
    await state.reset_state()
    await message.answer("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио")




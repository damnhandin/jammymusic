from aiogram import types
from aiogram.dispatcher import FSMContext


async def find_song_func(message: types.Message, state: FSMContext):
    await state.reset_state()
    await message.answer("Отправь мне название любой песни, либо ссылку на видео YouTube и я тебе отправлю аудио.")




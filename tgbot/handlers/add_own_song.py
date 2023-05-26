from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType, InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.callback_datas import action_callback
from tgbot.misc.states import JammyMusicStates


async def add_own_song_func(message):
    await JammyMusicStates.add_own_song.set()
    await message.answer("Пришлите свой трек")


async def get_own_song_to_add(message: types.Message, state: FSMContext):
    await state.reset_state()
    audio = message.audio.file_id
    try:
        await message.delete()
    except:
        pass
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Добавить в мои плейлисты",
                              callback_data=action_callback.new(cur_action="add_to_playlist"))]
    ])
    await message.answer_audio(audio=audio, reply_markup=reply_markup)


async def get_unknown_content_add_own_song_state(message):
    await message.answer("Похоже, что вы хотели добавить песню, но мы получили от вас неизвестный формат файла, "
                         "пожалуйста убедитесь в том, что вы действительно отправили аудио")


def register_add_own_music(dp: Dispatcher):
    dp.register_message_handler(add_own_song_func, Text("😎 Добавить свой трек"))
    dp.register_message_handler(get_own_song_to_add, state=JammyMusicStates.add_own_song,
                                content_types=ContentType.AUDIO)
    dp.register_message_handler(get_unknown_content_add_own_song_state, state=JammyMusicStates.add_own_song,
                                content_types=ContentType.ANY)


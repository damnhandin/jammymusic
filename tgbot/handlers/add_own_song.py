from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import MediaGroupFilter
from aiogram.types import ContentType
from tgbot.keyboards.inline import music_msg_keyboard


async def add_own_song_func(message, state):
    await state.reset_state()
    # await JammyMusicStates.add_own_song.set()
    await message.answer("Пришлите свой трек")


async def attach_many_songs_from_album(album: list[types.Message], media_group: Union[types.MediaGroup, None] = None):
    if media_group is None:
        media_group = types.MediaGroup()
    for song in album:
        media_group.attach({"media": song.audio.file_id,
                            "type": "audio"})
    return media_group


async def get_own_media_group_songs_to_add(message: types.Message, album):
    media_group = await attach_many_songs_from_album(album)
    await message.answer_media_group(media_group)
    await message.answer("Теперь выберите плейлист в который хотите добавить аудио", reply_markup=music_msg_keyboard)


async def get_own_song_to_add(message: types.Message):
    audio = message.audio.file_id
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer_audio(audio=audio, reply_markup=music_msg_keyboard)


async def get_own_song_to_add_media_group(message: types.Message):
    await message.answer("Если вы хотите импортировать сразу несколько треков за раз, вам необходимо зайти в меню "
                         "редактирования плейлиста, куда хотите добавить музыку и там нажать соответствующую кнопку")


def register_add_own_music(dp: Dispatcher):
    dp.register_message_handler(get_own_song_to_add, MediaGroupFilter(False), state="*",
                                content_types=ContentType.AUDIO)
    dp.register_message_handler(get_own_song_to_add_media_group, MediaGroupFilter(True), state="*",
                                content_types=ContentType.AUDIO)
    # dp.register_message_handler(get_own_media_group_songs_to_add, MediaGroupFilter(True), state="*",
    #                             content_types=ContentType.AUDIO)
    # dp.register_message_handler(get_unknown_content_add_own_song_state, state=JammyMusicStates.add_own_song,
    #                             content_types=ContentType.ANY)


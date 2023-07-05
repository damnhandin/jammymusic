import asyncio
from asyncio import get_running_loop
from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text, MediaGroupFilter
from aiogram.types import ContentType, InlineKeyboardMarkup, InlineKeyboardButton, MediaGroup, InputFile, \
    InputMediaAudio

from tgbot.keyboards.callback_datas import action_callback


async def add_own_song_func(message):
    # await JammyMusicStates.add_own_song.set()
    await message.answer("Пришлите свой трек")


async def attach_many_songs_from_album(album: list[types.Message], media_group: Union[types.MediaGroup, None] = None):
    if media_group is None:
        media_group = MediaGroup()
    for song in album:
        media_group.attach({"media": song.audio.file_id,
                            "type": "audio"})
    return media_group


async def get_own_media_group_songs_to_add(message: types.Message, album):
    print(album)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Добавить в мои плейлисты",
                              callback_data=action_callback.new(cur_action="add_to_playlist"))]
    ])
    media_group = await attach_many_songs_from_album(album)
    await message.answer_media_group(media_group)
    await message.answer("Теперь выберите плейлист в который хотите добавить аудио", reply_markup=reply_markup)


async def get_own_song_to_add(message: types.Message, album):
    print(album)
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


async def get_own_song_to_add_media_group(message: types.Message, album: list[types.Message]):
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


import concurrent.futures
from json import loads

import asyncio
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType, InputFile
from aiogram.utils.callback_data import CallbackData
from pytube import YouTube, Stream, StreamQuery
from youtubesearchpython import SearchVideos

from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback, playlist_callback, video_callback
from tgbot.keyboards.inline import confirm_start_keyboard
from tgbot.keyboards.reply import start_keyboard
from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def user_start_with_state(message):
    await message.answer("Вы уверены, что хотите перейти в главное меню?", reply_markup=confirm_start_keyboard)


async def user_confirm_start(cq, state):
    await state.reset_state(with_data=True)
    await cq.message.edit_text("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио",
                               reply_markup=start_keyboard)


async def delete_this_cq_message(cq: types.CallbackQuery):
    await cq.message.delete()


async def user_start(message: types.Message):
    await message.answer("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио",
                         reply_markup=start_keyboard)


class PlaylistPaginator:
    def __init__(self, telegram_id, edit_mode=False, cur_page=1, limit_per_page=5):
        self.telegram_id = telegram_id
        self.cur_page = cur_page
        self.limit_per_page = limit_per_page
        self.edit_mode = edit_mode

    async def create_playlist_keyboard(self, db: Database, add_track_mode=False):
        playlists = await db.select_user_playlists(self.telegram_id, self.limit_per_page,
                                                        (self.cur_page - 1) * self.limit_per_page)
        playlists_keyboard = await self.add_playlists_buttons(playlist_callback, playlists)
        await self.add_navigation_buttons(playlists_keyboard)
        await self.add_interaction_buttons(playlists_keyboard, add_track_mode=add_track_mode)

        return playlists_keyboard

    async def add_interaction_buttons(self, keyboard=None, add_track_mode=False):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()

        keyboard.row(
            InlineKeyboardButton("🔹Создать", callback_data=action_callback.new(cur_action="create_playlist")),
            InlineKeyboardButton("❌Отменить", callback_data=action_callback.new(cur_action="cancel_playlist"))
            if self.edit_mode or add_track_mode else
            InlineKeyboardButton("🔸Изменить", callback_data=action_callback.new(cur_action="edit_playlist"))
        )

    @staticmethod
    async def add_navigation_buttons(keyboard=None):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("◀️", callback_data=action_callback.new(cur_action="prev_page")),
            InlineKeyboardButton("🔄", callback_data=action_callback.new(cur_action="refresh")),
            InlineKeyboardButton("▶️", callback_data=action_callback.new(cur_action="next_page"))
        )
        return keyboard

    @staticmethod
    async def add_playlists_buttons(callback_data: CallbackData, playlists, keyboard=None):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()
        for playlist in playlists:
            keyboard.row(InlineKeyboardButton(playlist["playlist_title"],
                                              callback_data=callback_data.new(
                                                  playlist_id=playlist["playlist_id"]
                                              )))
        return keyboard


async def my_playlists(message: types.Message, db: Database, state: FSMContext):
    playlist_paginator = await get_paginator_from_state(message.from_user.id, state, PlaylistPaginator)
    reply_markup = await playlist_paginator.create_playlist_keyboard(db)
    await state.update_data(playlist_paginator=playlist_paginator)
    await message.answer('<b>Ваши плейлисты:</b>', reply_markup=reply_markup)
    try:
        await message.delete()
    except Exception:
        pass


async def run_blocking_io(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
    return result

async def search_music_func(mes: types.Message, db: Database):
    try:
        await mes.delete()
    except Exception:
        pass
    # (self, keyword, offset = 1, mode = 'json', max_results = 20, language = 'en', region = 'US'
    search_results = (await run_blocking_io(
        SearchVideos, mes.text, 1, 'json', 5, 'ru-RU', 'RU'
    )).result()
    if not search_results:
        await mes.answer("Никаких совпадений по запросу.")
        return
    search_results_json = await run_blocking_io(loads, search_results)
    reply_markup = InlineKeyboardMarkup()
    for res in search_results_json["search_result"]:
        # self.id, self.link, self.title, self.channel, self.duration
        reply_markup.row(InlineKeyboardButton(f"{res['duration']} {res['title']}",
                                              callback_data=video_callback.new(video_id=res["id"])))
        await db.add_video(res["id"], res["link"], res["title"])


    answer = f'<b>Результаты по запросу</b>: {mes.text}'
    # keyboard = InlineKeyboard(*kb_list, row_width=1)

    await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)


async def user_choose_video_cq(cq: types.CallbackQuery, callback_data, db: Database):
    video = await db.select_video_by_id(callback_data["video_id"])
    if not video:
        await cq.answer('Произошла ошибка! Повторите поиск!', cache_time=1)
        return
    yt_video = YouTube(video["link"])
    if not yt_video:
        await cq.message.answer('Произошла ошибка!')
        return
    # Здесь можно улучшить качество звука, если отсортировать по убыванию filesize
    # и выбрать самый большой, но в то же время подходящий файл
    audio_stream: StreamQuery = yt_video.streams.filter(type='audio')
    if audio_stream.last().filesize > 52428800:
        audio: Stream = audio_stream.first()
        if audio.filesize > 52428800:
            await cq.answer('Размер аудио слишком большой, невозможно отправить')
            return
    else:
        audio: Stream = audio_stream.last()

    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Добавить в мои плейлисты",
                              callback_data=action_callback.new(cur_action="add_to_playlist"))]
    ])
    await cq.message.answer_audio(InputFile(audio.download('download_cache')), title=audio.title,
                                  reply_markup=reply_markup, caption='Больше музыки на @jammy_music_bot')
    try:
        await cq.message.delete()
    except Exception as e:
        pass


async def add_to_playlist(cq: types.CallbackQuery, state, db):
    playlist_paginator = await get_paginator_from_state(cq.message.from_user.id, state, PlaylistPaginator)

    reply_markup = await playlist_paginator.create_playlist_keyboard(db)
    await cq.message.edit_caption("Больше музыки на @jammy_music_bot\n<b>Выберите плейлист:</b>",
                                  reply_markup=reply_markup)


async def create_playlist(cq: types.CallbackQuery, state):
    await JammyMusicStates.get_playlist_title.set()
    previous_text = cq.message.caption if cq.message.caption else cq.message.text
    await state.update_data(previous_text=previous_text)
    await state.update_data(msg_to_edit=cq.message)
    print(await state.get_data())
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=action_callback.new("cancel_create_playlist"))]
    ])
    if cq.message.caption:
        await cq.message.edit_caption("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
    else:
        await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)


async def get_playlist_title_and_set(message: types.Message, config: Config, state: FSMContext):
    if len(message.text) >= config.misc.playlist_title_length_limit:
        await message.answer(f"Ваше название слишком длинное, максимальная допустимая длина "
                             f"{config.misc.playlist_title_length_limit} символов, напишите название снова.")
        return
    await state.reset_state(with_data=False)
    async with state.proxy() as data:
        data["playlist_title"] = message.text
        msg_to_edit = data.get("msg_to_edit")
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(
                                  cur_action="confirm_creation"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(
                                  cur_action="cancel_creation"
                              ))]
    ])
    if msg_to_edit:
        if msg_to_edit.caption:
            await msg_to_edit.edit_caption(f"Создать плейлист с названием: <b>{message.text}</b>?",
                                           reply_markup=reply_markup)
        else:
            await msg_to_edit.edit_text(f"Создать плейлист с названием: <b>{message.text}</b>?",
                                        reply_markup=reply_markup)
    else:
        await message.answer(f"Создать плейлист с названием: <b>{message.text}</b>?", reply_markup=reply_markup)
    try:
        await message.delete()
    except:
        pass

async def get_paginator_from_state(tg_id, state, paginator_class=PlaylistPaginator):
    playlist_paginator = (await state.get_data()).get("playlist_paginator")
    if playlist_paginator is None:
        playlist_paginator = paginator_class(tg_id)
    return playlist_paginator

async def confirm_creation_playlist(cq, state: FSMContext, db: Database):
    async with state.proxy() as data:
        playlist_title = data["playlist_title"]
        previous_message = data.get("previous_message")
        await db.add_new_playlist(cq.from_user.id, playlist_title)
    playlist_paginator = await get_paginator_from_state(cq.from_user.id, state, PlaylistPaginator)
    reply_markup = await playlist_paginator.create_playlist_keyboard(db)
    if cq.message.caption:
        await cq.message.edit_caption(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                      reply_markup=reply_markup)
    else:
        await cq.message.edit_text(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                   reply_markup=reply_markup)


async def cancel_creation_playlist(cq, state, db):
    pass


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, CommandStart())
    dp.register_message_handler(user_start_with_state, CommandStart(), state="*")
    dp.register_callback_query_handler(create_playlist, action_callback.filter(cur_action="create_playlist"))
    dp.register_message_handler(get_playlist_title_and_set, state=JammyMusicStates.get_playlist_title,
                                content_types=ContentType.TEXT)
    dp.register_callback_query_handler(user_confirm_start, action_callback.filter(cur_action="confirm_to_start_menu"),
                                       state="*")
    dp.register_message_handler(my_playlists, Text("🎧 Мои плейлисты"))
    dp.register_callback_query_handler(my_playlists, action_callback.filter(
        cur_action=["cancel_create_playlist",
                    "cancel_creation"]),
                                       state="*")
    dp.register_callback_query_handler(delete_this_cq_message,
                                       action_callback.filter(cur_action="cancel_to_start_menu"),
                                       state="*")
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)
    dp.register_callback_query_handler(user_choose_video_cq, video_callback.filter())
    dp.register_callback_query_handler(add_to_playlist, action_callback.filter(cur_action="add_to_playlist"))
    dp.register_callback_query_handler(confirm_creation_playlist,
                                       action_callback.filter(cur_action="confirm_creation"))
    dp.register_callback_query_handler(cancel_creation_playlist,
                                       action_callback.filter(cur_action="cancel_creation"))

import concurrent.futures
from json import loads

import asyncio
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
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
    def __init__(self, db: Database, telegram_id, edit_mode=False, cur_page=1, limit_per_page=5):
        self.telegram_id = telegram_id
        self.cur_page = cur_page
        self.limit_per_page = limit_per_page
        self.edit_mode = edit_mode
        self.db = db

    async def create_playlist_preview_keyboard(self):
        playlists = await self.db.select_user_playlists(self.telegram_id, self.limit_per_page,
                                                        (self.cur_page - 1) * self.limit_per_page)
        playlists_keyboard = InlineKeyboardMarkup()
        for playlist in playlists:
            playlists_keyboard.row(InlineKeyboardButton(playlist["playlist_title"],
                                                        callback_data=playlist_callback.new(
                                                            playlist_id=playlist["playlist_id"])))
        playlists_keyboard.row(
            InlineKeyboardButton("◀️", callback_data=action_callback.new(cur_action="prev_page")),
            InlineKeyboardButton("🔄", callback_data=action_callback.new(cur_action="refresh")),
            InlineKeyboardButton("▶️", callback_data=action_callback.new(cur_action="next_page"))
        )
        playlists_keyboard.row(
            InlineKeyboardButton("🔹Создать", callback_data=action_callback.new(cur_action="create_playlist")),
            InlineKeyboardButton("❌Отменить", callback_data=action_callback.new(cur_action="cancel_edit_playlist"))
            if self.edit_mode else
            InlineKeyboardButton("🔸Изменить", callback_data=action_callback.new(cur_action="edit_playlist"))
        )
        return playlists_keyboard


async def my_playlists(message: types.Message, db: Database, state: FSMContext):
    playlist_paginator = (await state.get_data()).get("playlist_paginator")
    if playlist_paginator is None:
        playlist_paginator = PlaylistPaginator(db, message.from_user.id)
    reply_markup = await playlist_paginator.create_playlist_preview_keyboard()
    await state.update_data(playlist_paginator=playlist_paginator)
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer('<b>Ваши плейлисты:</b>', reply_markup=reply_markup)

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
    print(search_results)
    if not search_results:
        await mes.answer("Никаких совпадений по запросу.")
        return
    search_results_json = await run_blocking_io(loads, search_results)
    reply_markup = InlineKeyboardMarkup()
    for res in search_results_json["search_result"]:
        # self.id, self.link, self.title, self.channel, self.duration
        reply_markup.row(InlineKeyboardButton(f"{res['duration']} {res['title']}",
                                              callback_data=video_callback.new(video_id=res["id"])))
        print(res["title"])
        await db.add_video(res["id"], res["link"], res["title"])


    answer = f'<b>Результаты по запросу</b>: {mes.text}'
    # keyboard = InlineKeyboard(*kb_list, row_width=1)

    await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)


async def create_playlist(cq: types.CallbackQuery):
    await JammyMusicStates.get_playlist_title.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=action_callback.new("cancel_create_playlist"))]
    ])
    await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)


async def get_playlist_title_and_set(message: types.Message, config: Config, state):
    if len(message.text) >= config.misc.playlist_title_length_limit:
        await message.answer(f"Ваше название слишком длинное, максимальная допустимая длина "
                             f"{config.misc.playlist_title_length_limit} символов, напишите название снова.")
        return
    await state.reset_state()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(
                                  cur_action="confirm_creation"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(
                                  cur_action="cancel_creation"
                              ))]
    ])
    await message.answer(f"Создать плейлист с названием: <b>{message.text}</b>?", reply_markup=reply_markup)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, CommandStart())
    dp.register_message_handler(user_start_with_state, CommandStart(), state="*")
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


import concurrent.futures
import io
from json import loads

import asyncio
from math import ceil

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType, InputFile, MediaGroup, \
    InputMediaAudio
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from pytube import YouTube, Stream, StreamQuery
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import SearchVideos

from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback, playlist_callback, video_callback, edit_playlist_callback, \
    playlist_action
from tgbot.keyboards.inline import confirm_start_keyboard
from tgbot.keyboards.reply import start_keyboard
from tgbot.misc.exceptions import PlaylistNotFound, LimitTracksInPlaylist
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

    async def create_playlist_keyboard(self, db: Database, add_track_mode):
        print(self.limit_per_page)
        print((self.cur_page - 1) * self.limit_per_page)
        print(self.cur_page)
        playlists = await db.select_user_playlists(self.telegram_id, self.limit_per_page,
                                                   (self.cur_page - 1) * self.limit_per_page)

        print(playlists)
        playlists_keyboard = await self.add_playlists_buttons(playlists)
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

    async def add_playlists_buttons(self, playlists, keyboard=None):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()
        if self.edit_mode:
            callback_data = edit_playlist_callback
        else:
            callback_data = playlist_callback

        for playlist in playlists:
            keyboard.row(InlineKeyboardButton(playlist["playlist_title"],
                                              callback_data=callback_data.new(
                                                  playlist_id=playlist["playlist_id"]
                                              )))
        return keyboard

    async def next_page_navigation(self, db, count_of_pages, add_track_mode=False):
        if self.cur_page + 1 > count_of_pages:
            self.cur_page = 1
        else:
            self.cur_page += 1
        keyboard = await self.create_playlist_keyboard(db, add_track_mode)
        return keyboard

    async def prev_page_navigation(self, db, count_of_pages, add_track_mode=False):
        if self.cur_page - 1 < 1:
            self.cur_page = count_of_pages
        else:
            self.cur_page -= 1
        keyboard = await self.create_playlist_keyboard(db, add_track_mode)
        return keyboard


async def my_playlists(message: types.Message, db: Database, state: FSMContext):
    playlist_paginator = await get_paginator_from_state(message.from_user.id, state, PlaylistPaginator)
    playlist_paginator.edit_mode = False
    reply_markup = await playlist_paginator.create_playlist_keyboard(db, add_track_mode=bool(message.audio))
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
    try:
        audio_stream: StreamQuery = yt_video.streams.filter(type='audio')
    except AgeRestrictedError:
        await cq.message.answer("Данная музыка ограничена по возрасту")
        return
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
    # Через буфер
    audio_file = io.BytesIO()
    await run_blocking_io(audio.stream_to_buffer, audio_file)
    # audio.stream_to_buffer(audio_file)
    audio_file.seek(0)
    # Через скачивание файла в папку
    # audio.download('download_cache')
    await cq.message.answer_audio(InputFile(audio_file), title=audio.title,
                                  reply_markup=reply_markup, caption='Больше музыки на @jammy_music_bot')
    try:
        await cq.message.delete()
    except Exception as e:
        pass


async def add_to_playlist(cq: types.CallbackQuery, state, db):
    playlist_paginator = await get_paginator_from_state(cq.from_user.id, state, PlaylistPaginator)
    await state.update_data(previous_text=cq.message.caption)
    await state.update_data(previous_reply_markup=cq.message.reply_markup)
    reply_markup = await playlist_paginator.create_playlist_keyboard(db, add_track_mode=bool(cq.message.audio))
    await cq.message.edit_caption("Больше музыки на @jammy_music_bot\n<b>Выберите плейлист:</b>",
                                  reply_markup=reply_markup)


async def create_playlist(cq: types.CallbackQuery, state):
    await JammyMusicStates.get_playlist_title.set()
    await state.update_data(msg_to_edit=cq.message)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=action_callback.new("cancel_create_playlist"))]
    ])
    if cq.message.caption:
        await cq.message.edit_caption("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
    else:
        await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)


async def get_playlist_title_and_set(message: types.Message, config: Config, state: FSMContext):
    if len(message.text) >= config.misc.playlist_title_length_limit:
        msg_to_edit = await message.answer(
            f"Ваше название слишком длинное, максимальная допустимая длина "
            f"{config.misc.playlist_title_length_limit} символов, напишите название снова.")
        await state.update_data(msg_to_edit=msg_to_edit)
        return
    async with state.proxy() as data:
        data["playlist_title"] = message.text
        msg_to_edit = data.get("msg_to_edit")
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(
                                  cur_action="confirm_playlist_title"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(
                                  cur_action="cancel_creation"
                              ))]
    ])
    state_name = await state.get_state()
    if state_name is JammyMusicStates.get_playlist_title.state:
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
    else:
        if msg_to_edit:
            await msg_to_edit.edit_text(f"Изменить название на <b>{message.text}</b>?",
                                        reply_markup=reply_markup)
        else:
            await message.answer(f"Изменить название на <b>{message.text}</b>?",
                                 reply_markup=reply_markup)

async def get_paginator_from_state(tg_id, state: FSMContext, paginator_class=PlaylistPaginator):
    playlist_paginator = (await state.get_data()).get("playlist_paginator")
    if playlist_paginator is None:
        playlist_paginator = paginator_class(tg_id)
    await state.update_data(playlist_paginator=playlist_paginator)
    return playlist_paginator


async def confirm_creation_playlist(cq: types.CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await state.reset_state()
    try:
        await cq.message.delete()
    except:
        pass
    try:
        playlist_title = data["playlist_title"]
        previous_message = data.get("previous_text")
    except KeyError:
        await cq.message.delete_reply_markup()
        return
    await db.add_new_playlist(cq.from_user.id, playlist_title)
    playlist_paginator = await get_paginator_from_state(cq.from_user.id, state, PlaylistPaginator)
    reply_markup = await playlist_paginator.create_playlist_keyboard(db, add_track_mode=bool(cq.message.audio))
    if cq.message.caption:
        await cq.message.edit_caption(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                      reply_markup=reply_markup)
    else:
        await cq.message.edit_text(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                   reply_markup=reply_markup)


async def cancel_creation_playlist(cq, state, db):
    await state.reset_state(with_data=False)
    paginator: PlaylistPaginator = await get_paginator_from_state(cq.from_user.id, state)
    async with state.proxy() as data:
        previous_text = data.get("previous_text")
        reply_markup = data.get("previous_reply_markup")
        if reply_markup is None:
            reply_markup = await paginator.create_playlist_keyboard(db, add_track_mode=bool(cq.message.audio))
        if cq.message.caption:
            await cq.message.edit_caption(previous_text if previous_text else "<b>Ваши плейлисты:</b>",
                                          reply_markup=reply_markup)
        else:
            await cq.message.edit_text(previous_text if previous_text else "<b>Ваши плейлисты:</b>",
                                       reply_markup=reply_markup)


async def cancel_playlist_func(cq: types.CallbackQuery, db, state):
    if cq.message.audio:
        async with state.proxy() as data:
            previous_text = data.get("previous_text")
            previous_reply_markup = data.get("previous_reply_markup")
            if previous_text:
                await cq.message.edit_caption(previous_text, reply_markup=previous_reply_markup)
            else:
                await cq.message.edit_reply_markup(reply_markup=previous_reply_markup)
    else:
        paginator: PlaylistPaginator = await get_paginator_from_state(cq.from_user.id, state)
        paginator.edit_mode = False
        reply_markup = await paginator.create_playlist_keyboard(db, bool(cq.message.audio))
        await cq.message.edit_text("<b>Ваши плейлисты</b>", reply_markup=reply_markup)


async def generate_edit_playlist_msg(playlist, telegram_id, playlist_id, db):
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📝Изм. название",
                              callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                cur_action="change_playlist_title")),
         InlineKeyboardButton("🎶Добавить",
                              callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                 cur_action="add_music_to_playlist"))],
        [
            InlineKeyboardButton("🎶Убрать",
                                 callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                   cur_action="delete_music_from_playlist")),
            InlineKeyboardButton("❌Удалить плейлист",
                                 callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                   cur_action="delete_playlist"))
        ],
        [
            InlineKeyboardButton("Назад",
                                 callback_data=action_callback.new(cur_action="back_to_playlist_menu"))
        ]
    ])
    msg_text = f"📝<b>Название:</b>\n{playlist['playlist_title']}\n\n" \
               f"🎶<b>Плейлист:</b>\n"
    try:
        tracks = await db.select_user_tracks_from_playlist(telegram_id, playlist_id)
    except PlaylistNotFound:
        raise PlaylistNotFound
    msg_text += "\n".join(f"{num_track}) {track['track_title']}" for num_track, track in enumerate(tracks,
                                                                                                   start=1))
    return msg_text, reply_markup


async def choose_playlist(cq: types.CallbackQuery, callback_data, state, db: Database):
    print(callback_data)
    if cq.message.audio:
        try:
            await db.add_track_into_playlist(cq.from_user.id, cq.message.audio.file_id,
                                             cq.message.audio.title,
                                             callback_data["playlist_id"])
        except PlaylistNotFound:
            await cq.answer("Плейлист не был найден")
        except LimitTracksInPlaylist:
            await cq.answer("Достигнут лимит на количество треков в одном плейлисте")
        else:
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("Добавить в мои плейлисты",
                                      callback_data=action_callback.new(cur_action="add_to_playlist"))]
            ])
            try:
                await cq.message.edit_caption("Трек был успешно добавлен\nБольше музыки на @jammy_music_bot",
                                              reply_markup=reply_markup)
            except:
                pass
    else:
        paginator = await get_paginator_from_state(cq.from_user.id, state)
        if not paginator.edit_mode:
            print("hereeeeeeee")
            try:
                result = await db.select_user_tracks_from_playlist(cq.from_user.id, callback_data["playlist_id"])
            except PlaylistNotFound:
                await cq.answer("Плейлист не был найден")
            else:
                counter = 0
                media_group = MediaGroup()
                print("hereeeeeeeeee")
                print(result)
                for track in result:
                    counter += 1
                    media_group.attach(InputMediaAudio(media=track["track_id"]))
                    if counter == 10:
                        await cq.message.answer_media_group(media_group)
                        counter = 0
                        media_group = MediaGroup()
                else:
                    if counter != 0:
                        await cq.message.answer_media_group(media_group)
        else:
            print(1)
            playlist = await db.select_user_playlist(callback_data["playlist_id"])
            try:
                msg_text, reply_markup = await generate_edit_playlist_msg(playlist, cq.from_user.id,
                                                                          callback_data["playlist_id"], db)
            except PlaylistNotFound:
                await cq.answer("Плейлист не был найден")
                return
            await cq.message.edit_text(msg_text, reply_markup=reply_markup)


async def page_navigation(cq, callback_data, state, db: Database):
    paginator = await get_paginator_from_state(cq.from_user.id, state)
    count_of_pages = ceil((await db.count_of_user_playlists(cq.from_user.id)) / paginator.limit_per_page)
    if count_of_pages == 0:
        count_of_pages = 1
    if callback_data["cur_action"] == "prev_page":
        reply_markup = await paginator.prev_page_navigation(db, count_of_pages, add_track_mode=bool(cq.message.audio))
    else:
        reply_markup = await paginator.next_page_navigation(db, count_of_pages, add_track_mode=bool(cq.message.audio))
    try:
        await cq.message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
    await cq.answer()


async def start_edit_mode(cq, state, db):
    paginator = await get_paginator_from_state(cq.from_user.id, state)
    paginator.edit_mode = True
    keyboard = await paginator.create_playlist_keyboard(db, add_track_mode=False)
    await cq.message.edit_reply_markup(reply_markup=keyboard)


async def change_playlist_title(cq, state, callback_data, db):
    await JammyMusicStates.get_new_playlist_title.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=action_callback.new("cancel_create_playlist"))]
    ])
    msg_to_edit = await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
    await state.update_data(msg_to_edit=msg_to_edit, playlist_id=callback_data["playlist_id"])


async def get_and_set_new_playlist_title(message: types.Message, config, state, db):
    if len(message.text) >= config.misc.playlist_title_length_limit:
        msg_to_edit = await message.answer(f"Ваше название слишком длинное, максимальная допустимая длина "
                             f"{config.misc.playlist_title_length_limit} символов, напишите название снова.")
        await state.update_data(msg_to_edit=msg_to_edit)
        return
    await state.reset_state(with_data=False)


async def confirm_edit_playlist(cq, callback_data, state: FSMContext, db):
    data = await state.get_data()
    await state.reset_state()
    try:
        await cq.message.delete()
    except:
        pass
    try:
        playlist_title = data["playlist_title"]
        playlist_id = data["playlist_id"]
    except KeyError:
        await cq.message.delete_reply_markup()
        return
    await db.edit_playlist_title(playlist_id, playlist_title, cq.from_user.id)
    playlist = await db.select_user_playlist(playlist_id)
    try:
        msg_text, reply_markup = await generate_edit_playlist_msg(playlist, cq.from_user.id,
                                                                  playlist_id, db)
    except PlaylistNotFound:
        await cq.answer("Плейлист не был найден")
        return
    msg_to_edit = callback_data.get("msg_to_edit")
    if msg_to_edit:
        await msg_to_edit.edit_text(msg_text, reply_markup=reply_markup)
    else:
        await cq.message.answer(msg_text, reply_markup=reply_markup)



def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, CommandStart())
    dp.register_message_handler(user_start_with_state, CommandStart(), state="*")
    dp.register_callback_query_handler(create_playlist, action_callback.filter(cur_action="create_playlist"))
    dp.register_message_handler(get_playlist_title_and_set, state=[JammyMusicStates.get_playlist_title,
                                JammyMusicStates.get_new_playlist_title],
                                content_types=ContentType.TEXT)
    dp.register_callback_query_handler(user_confirm_start, action_callback.filter(cur_action="confirm_to_start_menu"),
                                       state="*")
    dp.register_message_handler(my_playlists, Text("🎧 Мои плейлисты"))
    dp.register_callback_query_handler(cancel_creation_playlist, action_callback.filter(
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
                                       action_callback.filter(cur_action="confirm_playlist_title"),
                                       state=JammyMusicStates.get_playlist_title)

    dp.register_callback_query_handler(cancel_playlist_func, action_callback.filter(cur_action="cancel_playlist"))
    dp.register_callback_query_handler(choose_playlist, playlist_callback.filter())
    dp.register_callback_query_handler(choose_playlist, edit_playlist_callback.filter())
    dp.register_callback_query_handler(page_navigation, action_callback.filter(cur_action=["prev_page", "next_page"]))
    dp.register_callback_query_handler(start_edit_mode, action_callback.filter(cur_action="edit_playlist"))
    dp.register_callback_query_handler(change_playlist_title,
                                       playlist_action.filter(cur_action="change_playlist_title"))
    # dp.register_callback_query_handler(add_music_to_playlist,
    #                                    action_callback.filter(cur_action="add_music_to_playlist")
    # dp.register_callback_query_handler(delete_music_from_playlist,
    #                                    action_callback.filter(cur_action="delete_music_from_playlist")
    # dp.register_callback_query_handler(delete_playlist,
    #                                    action_callback.filter(cur_action="delete_playlist")
    # dp.register_callback_query_handler(back_to_playlist_menu,
    #                                    action_callback.filter(cur_action="back_to_playlist_menu")
    dp.register_callback_query_handler(confirm_edit_playlist,
                                       action_callback.filter(cur_action="confirm_playlist_title"),
                                       state=JammyMusicStates.get_new_playlist_title)
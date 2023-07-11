import concurrent.futures
import io

import asyncio
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, MediaGroupFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType, InputFile, MediaGroup, \
    InputMediaAudio
from aiogram.utils.exceptions import MessageNotModified, InvalidQueryID
from pytube import YouTube, Stream
from pytube.exceptions import AgeRestrictedError

from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback, playlist_callback, video_callback, edit_playlist_callback, \
    playlist_action, playlist_navg_callback
from tgbot.keyboards.inline import confirm_start_keyboard
from tgbot.keyboards.reply import start_keyboard
from tgbot.misc.exceptions import PlaylistNotFound, LimitTracksInPlaylist, WrongSongNumber
from tgbot.misc.misc_funcs import delete_all_messages_from_data, catch_exception_if_playlist_is_not_available
from tgbot.misc.states import JammyMusicStates
from tgbot.models.classes.paginator import PlaylistPaginator
from tgbot.models.db_utils import Database


async def user_start_with_state(message):
    await message.answer("Вы уверены, что хотите перейти в главное меню?", reply_markup=confirm_start_keyboard)


async def user_confirm_start(cq, state):
    await state.reset_state(with_data=True)
    try:
        await cq.message.delete()
    except:
        pass
    await cq.message.answer("Отправь мне название любой песни, либо ссылку на видео YouTube и я тебе отправлю аудио.",
                            reply_markup=start_keyboard)


async def delete_this_cq_message(cq: types.CallbackQuery):
    await cq.message.delete()


async def user_start(message: types.Message):
    await message.answer("Отправь мне название любой песни, либо ссылку на видео YouTube и я тебе отправлю аудио.",
                         reply_markup=start_keyboard)


async def my_playlists(message: types.Message, playlist_pg, state, db: Database):
    data = await state.get_data()
    await state.reset_state()
    await delete_all_messages_from_data(data)  # fun function
    reply_markup = await playlist_pg.create_playlist_keyboard(message.from_user.id,
                                                              db, add_track_mode=bool(message.audio))
    await message.answer('<b>Ваши плейлисты:</b>', reply_markup=reply_markup)
    try:
        await message.delete()
    except Exception:
        pass


async def run_cpu_bound(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
    return result


async def run_blocking_io(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
    return result


async def user_choose_video_cq(cq: types.CallbackQuery, callback_data):
    video_id = callback_data["video_id"]
    if not video_id:
        await cq.answer('Произошла ошибка! Повторите поиск!', cache_time=1)
        return
    yt_link = f"https://www.youtube.com/watch?v={video_id}"
    try:
        yt_video = YouTube(yt_link)
    except:
        yt_link = f"https://music.youtube.com/watch?v={video_id}"
        yt_video = YouTube(yt_link)
    if not yt_video:
        await cq.message.answer('Произошла ошибка!')
        return

    # Здесь можно улучшить качество звука, если отсортировать по убыванию filesize
    # и выбрать самый большой, но в то же время подходящий файл
    try:
        audio: Stream = yt_video.streams.get_audio_only()
    except AgeRestrictedError:
        await cq.message.answer("Данная музыка ограничена по возрасту")
        return
    if audio.filesize > 50000000:
        await cq.answer('Размер аудио слишком большой, невозможно отправить')
        return
    try:
        await cq.answer("Ищем информацию по данному запросу!")
    except InvalidQueryID:
        await cq.message.answer("Ищем информацию по данному запросу!")
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Добавить в мои плейлисты",
                              callback_data=action_callback.new(cur_action="add_to_playlist"))]
    ])
    # Через буфер
    audio_file = io.BytesIO()
    await run_blocking_io(audio.stream_to_buffer, audio_file)
    await run_blocking_io(audio_file.seek, 0)
    await cq.message.answer_audio(InputFile(audio_file), title=audio.title,
                                  performer=yt_video.author if yt_video.author else None,
                                  reply_markup=reply_markup, caption='Больше музыки на @jammy_music_bot')
    # try:
    #     await cq.message.delete()
    # except Exception:
    #     pass


async def add_to_playlist(cq: types.CallbackQuery, playlist_pg, state, db):
    await state.update_data(previous_text=cq.message.caption)
    await state.update_data(previous_reply_markup=cq.message.reply_markup)
    reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db,
                                                              add_track_mode=bool(cq.message.audio))
    await cq.message.edit_caption("Больше музыки на @jammy_music_bot\n<b>Выберите плейлист:</b>",
                                  reply_markup=reply_markup)


async def create_playlist(cq: types.CallbackQuery, callback_data, state):
    await JammyMusicStates.get_playlist_title.set()
    await state.update_data(msg_to_edit=cq.message)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=playlist_navg_callback.new(
            cur_page=callback_data["cur_page"], cur_mode=callback_data["cur_mode"],
            cur_action="cancel_playlist"))]
    ])
    try:
        if cq.message.caption:
            await cq.message.edit_caption("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
        else:
            await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def get_playlist_title_and_set(message: types.Message, config: Config, state: FSMContext, db):
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
    if state_name == JammyMusicStates.get_playlist_title.state:
        if msg_to_edit:
            try:
                if msg_to_edit.caption:
                    await msg_to_edit.edit_caption(f"Создать плейлист с названием: <b>{message.text}</b>?",
                                                   reply_markup=reply_markup)
                else:
                    await msg_to_edit.edit_text(f"Создать плейлист с названием: <b>{message.text}</b>?",
                                                reply_markup=reply_markup)
            except MessageNotModified:
                pass

        else:
            await message.answer(f"Создать плейлист с названием: <b>{message.text}</b>?", reply_markup=reply_markup)
        try:
            await message.delete()
        except:
            pass
    else:
        data = await state.get_data()
        if await catch_exception_if_playlist_is_not_available(message, data["playlist_id"], db,
                                                              datetime.now(), state) is not True:
            return
        if msg_to_edit:
            try:
                await msg_to_edit.edit_text(f"Изменить название на <b>{message.text}</b>?",
                                            reply_markup=reply_markup)
            except MessageNotModified:
                pass
        else:
            await message.answer(f"Изменить название на <b>{message.text}</b>?",
                                 reply_markup=reply_markup)


async def confirm_creation_playlist(cq: types.CallbackQuery, playlist_pg, state: FSMContext, db: Database):
    data = await state.get_data()
    await state.reset_state()
    try:
        playlist_title = data["playlist_title"]
        previous_message = data.get("previous_text")
    except KeyError:
        await cq.message.delete_reply_markup()
        return
    await db.add_new_playlist(cq.from_user.id, playlist_title)
    reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db,
                                                              add_track_mode=bool(cq.message.audio))
    try:
        if cq.message.caption:
            await cq.message.edit_caption(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                          reply_markup=reply_markup)
        else:
            await cq.message.edit_text(previous_message if previous_message else "<b>Ваши плейлисты:</b>",
                                       reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def cancel_creation_playlist(cq, playlist_pg, state, db):
    await state.reset_state(with_data=False)
    reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db,
                                                              add_track_mode=bool(cq.message.audio))
    try:
        if cq.message.audio:
            await cq.message.edit_caption("<b>Ваши плейлисты:</b>",
                                          reply_markup=reply_markup)
        else:
            await cq.message.edit_text("<b>Ваши плейлисты:</b>",
                                       reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def cancel_playlist_func(cq: types.CallbackQuery, callback_data, playlist_pg, db, state):
    await state.reset_state()
    if cq.message.audio:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("Добавить в мои плейлисты",
                                  callback_data=action_callback.new(cur_action="add_to_playlist"))]
        ])
        try:
            await cq.message.edit_caption("Больше музыки на @jammy_music_bot", reply_markup=reply_markup)
        except:
            pass
    else:
        try:
            reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id,
                                                                      db,
                                                                      cur_page=callback_data["cur_page"])
        except KeyError:
            await cq.message.delete_reply_markup()
            return
        try:
            await cq.message.edit_text("<b>Ваши плейлисты:</b>", reply_markup=reply_markup)
        except MessageNotModified:
            pass


async def generate_edit_playlist_msg(playlist, telegram_id, playlist_id, db, cur_page=1):
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📝Изм. название",
                              callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                cur_action="change_playlist_title",
                                                                cur_page=cur_page)),
         InlineKeyboardButton("🎶Добавить",
                              callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                cur_action="add_music_to_playlist",
                                                                cur_page=cur_page))],
        [
            InlineKeyboardButton("🎶Убрать",
                                 callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                   cur_action="delete_music_from_playlist",
                                                                   cur_page=cur_page)),
            InlineKeyboardButton("❌Удалить плейлист",
                                 callback_data=playlist_action.new(playlist_id=playlist_id,
                                                                   cur_action="delete_playlist",
                                                                   cur_page=cur_page))
        ],
        [
            InlineKeyboardButton("Назад",
                                 callback_data=playlist_navg_callback.new(
                                     cur_page=cur_page,
                                     cur_mode="edit_mode",
                                     cur_action="back_to_playlist_menu"
                                                                          ))
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


async def generate_edit_menu_text_message(db, playlist, playlist_id, user_telegram_id, msg_text=None):
    if msg_text is None:
        msg_text = f"📝<b>Название:</b>\n{playlist['playlist_title']}\n\n" \
                   f"🎶<b>Плейлист:</b>\n"
    try:
        tracks = await db.select_user_tracks_from_playlist(user_telegram_id, playlist_id)
    except PlaylistNotFound:
        raise PlaylistNotFound
    msg_text = await format_tracks_to_numerated_list(tracks, msg_text=msg_text)

    return msg_text


async def format_tracks_to_numerated_list(tracks, msg_text=None):
    if msg_text is None:
        msg_text = ""
    msg_text += "\n".join(f"{num_track}) {track['track_title']}" for num_track, track in enumerate(tracks,
                                                                                                   start=1))
    return msg_text


async def choose_playlist(cq: types.CallbackQuery, callback_data, state, db: Database):
    if await catch_exception_if_playlist_is_not_available(
            cq, callback_data["playlist_id"], db, datetime.now(), state) is not True:
        return
    if cq.message.audio:
        try:
            audio_title = cq.message.audio.title if cq.message.audio.title else cq.message.audio.file_name
            await db.add_track_into_playlist(cq.from_user.id, cq.message.audio.file_id,
                                             audio_title,
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
                await cq.message.edit_caption("<b>Трек был успешно добавлен</b>\nБольше музыки на @jammy_music_bot",
                                              reply_markup=reply_markup)
            except:
                pass
    else:
        if callback_data["cur_mode"] == "default":
            try:
                result = await db.select_user_tracks_from_playlist(cq.from_user.id, callback_data["playlist_id"])
            except PlaylistNotFound:
                await cq.answer("Плейлист не был найден")
            else:
                if not result:
                    await cq.answer("У вас нет песен в этом плейлисте")
                    return
                counter = 0
                media_group = MediaGroup()
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
            playlist = await db.select_user_playlist(callback_data["playlist_id"])
            try:
                msg_text, reply_markup = await generate_edit_playlist_msg(playlist, cq.from_user.id,
                                                                          callback_data["playlist_id"], db,
                                                                          cur_page=callback_data["cur_page"])
            except PlaylistNotFound:
                await cq.answer("Плейлист не был найден")
                return
            try:
                await cq.message.edit_text(msg_text, reply_markup=reply_markup)
            except MessageNotModified:
                pass


async def page_navigation(cq, callback_data, playlist_pg: PlaylistPaginator, db: Database):
    count_of_pages = await playlist_pg.count_of_amount_pages_of_user_playlist(cq.from_user.id, db)
    if callback_data["cur_action"] == "prev_page":
        reply_markup = await playlist_pg.prev_page_navigation(cq.from_user.id, int(callback_data["cur_page"]),
                                                              callback_data["cur_mode"],
                                                              db, count_of_pages,
                                                              add_track_mode=bool(cq.message.audio))
    else:
        reply_markup = await playlist_pg.next_page_navigation(cq.from_user.id, int(callback_data["cur_page"]),
                                                              callback_data["cur_mode"],
                                                              db, count_of_pages,
                                                              add_track_mode=bool(cq.message.audio))
    try:
        await cq.message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
    finally:
        await cq.answer()


async def start_edit_mode(cq, playlist_pg, callback_data, db):
    keyboard = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db,
                                                          cur_page=callback_data["cur_page"],
                                                          cur_mode="edit_mode",
                                                          add_track_mode=False, edit_mode=True)
    await cq.message.edit_reply_markup(reply_markup=keyboard)


async def change_playlist_title(cq: types.CallbackQuery, callback_data, db, state):
    if await catch_exception_if_playlist_is_not_available(
            cq, callback_data["playlist_id"], db, datetime.now(), state) is not True:
        return
    await JammyMusicStates.get_new_playlist_title.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=playlist_action.new(
            playlist_id=callback_data["playlist_id"],
            cur_action="back_to_edit_menu",
            cur_page=callback_data["cur_page"]))]
    ])
    try:
        msg_to_edit = await cq.message.edit_text("<b>Введите название для плейлиста:</b>", reply_markup=reply_markup)
        await state.update_data(msg_to_edit=msg_to_edit, playlist_id=callback_data["playlist_id"])
    except MessageNotModified:
        pass


async def confirm_edit_playlist(cq, callback_data, state: FSMContext, db):
    data = await state.get_data()
    await state.reset_state()
    if await catch_exception_if_playlist_is_not_available(cq, data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
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
    try:
        if msg_to_edit:
            await msg_to_edit.edit_text(msg_text, reply_markup=reply_markup)
        else:
            await cq.message.answer(msg_text, reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def add_music_to_playlist(cq: types.CallbackQuery, callback_data, state, db):
    if await catch_exception_if_playlist_is_not_available(cq, callback_data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
    await JammyMusicStates.add_music_to_playlist.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отменить", callback_data=playlist_action.new(
            playlist_id=callback_data["playlist_id"],
            cur_action="back_to_edit_menu",
            cur_page=callback_data["cur_page"]))]
    ])
    try:
        await cq.message.edit_text("<b>Пришлите песню/песни для добавления:</b>",
                                   reply_markup=reply_markup)
    except MessageNotModified:
        pass
    finally:
        await state.update_data(msg_to_delete=cq.message, playlist_id=callback_data["playlist_id"])



async def delete_format_name_from_filename(filename: str):
    index = filename.find(".mp3")
    return filename[:index]


async def get_music_to_add_to_playlist_media_group(message: types.Message, album: list[types.Message], state, db):
    await state.reset_state(with_data=False)
    data = await state.get_data()
    if await catch_exception_if_playlist_is_not_available(message, data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
    for song in album:
        playlist_id = int(data["playlist_id"])
        if song.audio.title:
            audio_title = song.audio.title
        else:
            audio_title = await delete_format_name_from_filename(song.audio.file_name)
        await db.add_track_into_playlist(song.from_user.id, song.audio.file_id, audio_title, playlist_id)

    msg_to_delete = data["msg_to_delete"]
    try:
        await msg_to_delete.delete()
        await message.delete()
    except:
        pass
    await state.reset_data()
    await message.answer("Треки были успешно добавлены в плейлист, если что-то не было добавлено, убедитесь, что вы "
                         "отправляли все песни одним сообщением")


async def get_music_to_add_to_playlist(message: types.Message, state: FSMContext, db: Database):
    await state.reset_state(with_data=False)
    data = await state.get_data()
    playlist_id = int(data["playlist_id"])
    if await catch_exception_if_playlist_is_not_available(message, playlist_id, db, datetime.now(), state) is not True:
        return
    msg_to_delete = data["msg_to_delete"]
    if message.audio.title:
        audio_title = message.audio.title
    else:
        audio_title = await delete_format_name_from_filename(message.audio.file_name)
    await db.add_track_into_playlist(message.from_user.id, message.audio.file_id, audio_title, playlist_id)
    try:
        await msg_to_delete.delete()
        await message.delete()
    except:
        pass
    await state.reset_data()
    await message.answer("Трек был успешно добавлен в плейлист")


async def get_unknown_content_to_add_to_playlist(message):
    await message.answer("Похоже, что вы хотели добавить аудиофайл в плейлист, но вместо этого отправили неизвестный "
                         "формат медиафайла, либо просто текст, пожалуйста убедитесь, что отправляете именно "
                         "аудио.")


async def delete_playlist(cq: types.CallbackQuery, callback_data, db):
    if await catch_exception_if_playlist_is_not_available(cq, callback_data["playlist_id"], db,
                                                          datetime.now(), callback_data["playlist_id"]) is not True:
        return
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=playlist_action.new(playlist_id=callback_data["playlist_id"],
                                                                cur_action="confirm_delete_playlist",
                                                                cur_page=callback_data["cur_page"]
                                                                )),
         InlineKeyboardButton("❌",
                              callback_data=playlist_action.new(
                                  playlist_id=callback_data["playlist_id"],
                                  cur_action="back_to_edit_menu",
                                  cur_page=callback_data["cur_page"]
                              ))]
    ])
    try:
        await cq.message.edit_text("<b>Вы действительно хотите удалить плейлист?</b>", reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def confirm_delete_playlist(cq: types.CallbackQuery, playlist_pg: PlaylistPaginator,
                                  state, callback_data, db: Database):
    if await catch_exception_if_playlist_is_not_available(cq, callback_data["playlist_id"],
                                                          db, datetime.now(), state) is not True:
        return
    try:
        await db.delete_user_playlist(cq.from_user.id, int(callback_data["playlist_id"]))
    except PlaylistNotFound:
        try:
            await cq.message.edit_text("Плейлист не был найден")
        except MessageNotModified:
            pass
        return
    reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db, cur_page=callback_data["cur_page"],
                                                              cur_mode="edit_mode", edit_mode=True, check_cur_page=True)
    try:
        await cq.message.edit_text("<b>Ваши плейлисты:</b>", reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def back_to_playlist_menu(cq: types.CallbackQuery, callback_data, playlist_pg: PlaylistPaginator, db):
    cur_page = int(callback_data["cur_page"])
    reply_markup = await playlist_pg.create_playlist_keyboard(cq.from_user.id, db, cur_page=cur_page,
                                                              cur_mode=callback_data["cur_mode"], check_cur_page=True)
    try:
        await cq.message.edit_text("<b>Ваши плейлисты:</b>", reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def back_to_edit_menu(cq: types.CallbackQuery, callback_data, playlist_pg, state, db: Database):
    await state.reset_state()
    if await catch_exception_if_playlist_is_not_available(cq, callback_data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
    if cq.message.caption:
        return
    playlist = await db.select_user_playlist(callback_data["playlist_id"])
    if not playlist:
        reply_markup = await playlist_pg.create_playlist_keyboard(
            cq.from_user.id, db, cur_page=int(callback_data["cur_page"]),
            cur_mode="edit_mode",
            edit_mode=True,
            check_cur_page=True)
        try:
            await cq.message.edit_text("<b>Ваши плейлисты:</b>", reply_markup=reply_markup)
        except MessageNotModified:
            pass
        return
    msg_text, reply_markup = await generate_edit_playlist_msg(playlist, cq.from_user.id, callback_data["playlist_id"],
                                                              db, cur_page=callback_data["cur_page"])
    try:
        await cq.message.edit_text(msg_text, reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def delete_music_from_playlist(cq: types.CallbackQuery, callback_data, state, db: Database):
    if await catch_exception_if_playlist_is_not_available(cq, callback_data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
    count_of_songs = await db.count_song_in_user_playlist(int(callback_data["playlist_id"]))
    if count_of_songs == 0:
        await cq.answer("У вас нет песен в плейлисте!")
        return
    await JammyMusicStates.get_number_of_song_to_delete.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌Отмена",
                              callback_data=playlist_action.new(
                                  playlist_id=callback_data["playlist_id"],
                                  cur_action="back_to_edit_menu",
                                  cur_page=callback_data["cur_page"]
                              ))]
    ])
    msg_delete_reply_markup = await cq.message.answer(
        "<b>Введите номер трека, который хотите удалить:</b>", reply_markup=reply_markup)
    cur_page = callback_data["cur_page"]
    playlist_id = callback_data["playlist_id"]
    await state.update_data(msg_delete_reply_markup=msg_delete_reply_markup,
                            playlist_id=playlist_id,
                            cur_page=cur_page)


async def get_number_of_song_to_delete_func(message, playlist_pg, db: Database, state):
    data = await state.get_data()
    if await catch_exception_if_playlist_is_not_available(message, data["playlist_id"], db,
                                                          datetime.now(), state) is not True:
        return
    try:
        number_song = int(message.text)
        count_of_songs = await db.count_song_in_user_playlist(int(data["playlist_id"]))
        if number_song < 1 or number_song > count_of_songs:
            raise WrongSongNumber

    except ValueError:
        await message.answer("Пожалуйста введите номер песни, которую хотите удалить")
        return
    except WrongSongNumber:
        await message.answer("Вы вышли за диапазон песен, повторите попытку")
        return
    else:
        await state.reset_state()
        try:
            await db.delete_song_from_user_playlist(message.from_user.id, int(data["playlist_id"]), number_song)
        except PlaylistNotFound:
            await message.answer("Произошла ошибка, плейлист не был найден")
            return
        else:
            await data["msg_delete_reply_markup"].delete()
            playlist = await db.select_user_playlist(int(data["playlist_id"]))
            if not playlist:
                await playlist_pg.create_playlist_keyboard(message.from_user.id, db,
                                                           cur_page=data["cur_page"],
                                                           cur_mode="edit_mode",
                                                           edit_mode=True,
                                                           check_cur_page=True)
                return
            msg_text, reply_markup = await generate_edit_playlist_msg(playlist, message.from_user.id,
                                                                      data["playlist_id"],
                                                                      db, cur_page=data["cur_page"])
            await message.answer(msg_text, reply_markup=reply_markup)


async def get_unknown_content_to_delete_song_func(message):
    await message.answer("Похоже мы получили от вас неизвестный файл, вместо номера песни, которую хотите удалить.")


async def reset_state_delete_reply(cq: types.CallbackQuery, state):
    await state.reset_state()
    try:
        await cq.message.delete_reply_markup()
        await cq.answer("Отменено")
    except:
        pass


async def page_refresh(cq, callback_data, playlist_pg: PlaylistPaginator, db):
    count_of_pages = await playlist_pg.count_of_amount_pages_of_user_playlist(cq.from_user.id, db)
    reply_markup = await playlist_pg.refresh_page_navigation(cq.from_user.id, int(callback_data["cur_page"]),
                                                             callback_data["cur_mode"],
                                                             db, count_of_pages,
                                                             add_track_mode=bool(cq.message.audio))
    try:
        await cq.message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
    finally:
        await cq.answer()

def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, CommandStart())
    dp.register_message_handler(user_start_with_state, CommandStart(), state="*")
    dp.register_callback_query_handler(create_playlist, playlist_navg_callback.filter(cur_action="create_playlist"))
    dp.register_message_handler(get_playlist_title_and_set, state=[JammyMusicStates.get_playlist_title,
                                JammyMusicStates.get_new_playlist_title],
                                content_types=ContentType.TEXT)
    dp.register_callback_query_handler(user_confirm_start, action_callback.filter(cur_action="confirm_to_start_menu"),
                                       state="*")
    dp.register_callback_query_handler(cancel_creation_playlist, playlist_navg_callback.filter(
        cur_action=["cancel_create_playlist"]),
                                       state="*")
    dp.register_callback_query_handler(cancel_creation_playlist, action_callback.filter(cur_action="cancel_creation"),
                                       state="*")
    dp.register_callback_query_handler(delete_this_cq_message,
                                       action_callback.filter(cur_action="cancel_to_start_menu"),
                                       state="*")
    dp.register_callback_query_handler(user_choose_video_cq, video_callback.filter())
    dp.register_callback_query_handler(add_to_playlist, action_callback.filter(cur_action="add_to_playlist"))
    dp.register_callback_query_handler(confirm_creation_playlist,
                                       action_callback.filter(cur_action="confirm_playlist_title"),
                                       state=JammyMusicStates.get_playlist_title)

    dp.register_callback_query_handler(cancel_playlist_func, playlist_navg_callback.filter(
        cur_action="cancel_playlist"), state="*")
    dp.register_callback_query_handler(choose_playlist, playlist_callback.filter())
    dp.register_callback_query_handler(choose_playlist, edit_playlist_callback.filter())
    dp.register_callback_query_handler(page_navigation, playlist_navg_callback.filter(
        cur_action=["prev_page", "next_page"]))
    dp.register_callback_query_handler(page_refresh, playlist_navg_callback.filter(cur_action="page_refresh"))
    dp.register_callback_query_handler(start_edit_mode, playlist_navg_callback.filter(cur_action="edit_playlist"))
    dp.register_callback_query_handler(change_playlist_title,
                                       playlist_action.filter(cur_action="change_playlist_title"))
    dp.register_callback_query_handler(add_music_to_playlist,
                                       playlist_action.filter(cur_action="add_music_to_playlist"))
    dp.register_message_handler(get_music_to_add_to_playlist, MediaGroupFilter(is_media_group=False),
                                content_types=ContentType.AUDIO,
                                state=JammyMusicStates.add_music_to_playlist)
    dp.register_message_handler(get_music_to_add_to_playlist_media_group,  MediaGroupFilter(is_media_group=True),
                                content_types=ContentType.AUDIO,
                                state=JammyMusicStates.add_music_to_playlist)
    dp.register_callback_query_handler(delete_music_from_playlist,
                                       playlist_action.filter(cur_action="delete_music_from_playlist"))
    dp.register_callback_query_handler(delete_playlist,
                                       playlist_action.filter(cur_action="delete_playlist"))
    dp.register_callback_query_handler(back_to_playlist_menu,
                                       playlist_navg_callback.filter(cur_action="back_to_playlist_menu"))
    dp.register_callback_query_handler(confirm_edit_playlist,
                                       action_callback.filter(cur_action="confirm_playlist_title"),
                                       state=JammyMusicStates.get_new_playlist_title)
    dp.register_callback_query_handler(back_to_edit_menu,
                                       playlist_action.filter(cur_action="back_to_edit_menu"),
                                       state="*")
    dp.register_message_handler(get_unknown_content_to_add_to_playlist,
                                content_types=ContentType.ANY,
                                state=JammyMusicStates.add_music_to_playlist)
    dp.register_callback_query_handler(confirm_delete_playlist, playlist_action.filter(
        cur_action="confirm_delete_playlist"))
    dp.register_message_handler(get_number_of_song_to_delete_func,
                                content_types=ContentType.TEXT, state=JammyMusicStates.get_number_of_song_to_delete)
    dp.register_message_handler(get_unknown_content_to_delete_song_func,
                                content_types=ContentType.ANY, state=JammyMusicStates.get_number_of_song_to_delete)
    dp.register_callback_query_handler(reset_state_delete_reply,
                                       action_callback.filter(cur_action="reset_state_delete_reply"),
                                       state="*")

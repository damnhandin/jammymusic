import concurrent.futures
import asyncio
import io
from datetime import timedelta, datetime
from datetime import date as datetime_date
from typing import Union

import aiogram
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InputMedia, InlineKeyboardMarkup, InlineKeyboardButton
from pytube import Stream, YouTube

from tgbot.keyboards.callback_datas import video_callback
from tgbot.misc.exceptions import PlaylistNotAvailable, PlaylistNotFound, FileIsTooLarge
from tgbot.models.db_utils import Database


async def count_users_activity(attendance_data):
    today = datetime_date.today()
    print(attendance_data)
    one_week_ago = today - timedelta(days=7)
    count_today_activity = 0
    count_week_activity = 0
    for date in attendance_data.values():
        if date == today:
            count_today_activity += 1
        if date >= one_week_ago:
            count_week_activity += 1
    return count_today_activity, count_week_activity


async def admin_sending_func(send_func, receivers, media_content=None):
    count = 0
    for receiver in receivers:
        count += 1
        if count % 30 == 0:
            await asyncio.sleep(30)
        try:
            receiver_telegram_id = receiver.get("telegram_id") or receiver
            if media_content is None:
                await send_func(chat_id=receiver_telegram_id)
            else:
                await send_func(chat_id=receiver_telegram_id, media=media_content)
        except aiogram.exceptions.BotBlocked:
            continue
        except aiogram.exceptions.ToMuchMessages:
            await asyncio.sleep(30)


async def convert_album_to_media_group(album: [types.Message], media_group=None):
    if media_group is None:
        media_group = types.MediaGroup()
    for media in album:
        if media.photo:
            file = media.photo[-1]
            file_id = file.file_id
        else:
            file = media[media.content_type]
            file_id = file.file_id

        media_group.attach(InputMedia(media=file_id, caption=media["caption"], type=media.content_type))
    return media_group


async def write_tg_ids_to_bytes_io(users_ids):
    file = io.BytesIO()
    for user_id in users_ids:
        file.write(bytes(f"{user_id['telegram_id']}\n", "utf-8"))
    file.seek(0)
    return file


def convert_search_results_to_reply_markup(search_results):
    reply_markup = InlineKeyboardMarkup()
    for res in search_results:
        if res.get("id"):
            video_id = res.get("id")
            cur_emoji = "🎵"
            song_title = res.get("title")
        else:
            video_id = res.get("videoId")
            cur_emoji = "🎶"  # 🎶🎵
            song_artists = ", ".join([artist.get("name") for artist in res.get("artists")])
            if song_artists:
                song_title = f"{song_artists} - {res['title']}"
            else:
                song_title = res["title"]
        reply_markup.row(InlineKeyboardButton(f"{cur_emoji} {res['duration']} {song_title}",
                                              callback_data=video_callback.new(video_id=video_id)))
    return reply_markup


def filter_songs_without_correct_duration(video_searcher, searched_music=None, songs_limit=8):
    if searched_music is None:
        searched_music = list()
    while len(searched_music) < songs_limit:
        result = video_searcher.result().get("result")
        if not result:
            break
        for song in result:
            if song["duration"] != "LIVE" and song["duration"] is not None \
                    and ("hours" not in song["accessibility"]["duration"] and
                         "hour" not in song["accessibility"]["duration"]):
                song_duration = song["duration"].split(":")
                if len(song_duration) == 2:
                    if int(song_duration[0]) > 51:
                        continue
                searched_music.append(song)
            if len(searched_music) >= songs_limit:
                return searched_music
        video_searcher.next()
    return searched_music


async def choose_content_and_func_for_sending(data, users, bot):
    message_to_send = data.get("sending_message")
    if message_to_send is not None:
        return admin_sending_func(message_to_send.send_copy, users)
    media_group_to_send = data.get("sending_media_group")
    if media_group_to_send is not None:
        return admin_sending_func(bot.send_media_group, users, media_group_to_send)


async def delete_all_messages_from_data(data: dict):
    for item in data.values():
        if isinstance(item, types.Message):
            try:
                await item.delete()
            except Exception:
                continue


async def catch_exception_if_playlist_is_not_available(target: Union[types.CallbackQuery, types.Message],
                                                       playlist_id: Union[int, str], db: Database,
                                                       current_date: datetime.date,
                                                       state: FSMContext) -> bool:
    if isinstance(playlist_id, str):
        playlist_id = int(playlist_id)
    try:
        if (await check_if_user_playlist_is_available(playlist_id,
                                                      db, target.from_user.id, current_date)) is False:
            await target.answer("Плейлист недоступен")
            try:
                if isinstance(target, types.CallbackQuery):
                    await target.message.delete_reply_markup()
            except Exception:
                pass
            finally:
                await state.reset_state()
                return False

    except PlaylistNotFound:
        await target.answer("Плейлист недоступен")
        return False
    except PlaylistNotAvailable:
        await target.answer("Для использования плейлиста, необходимо приобрети подписку")
        return False
    return True


async def check_if_user_playlist_is_available(playlist_id, db, user_telegram_id, current_date) -> bool:
    playlist = await db.select_user_playlist(playlist_id)
    if not playlist:
        raise PlaylistNotFound
    if (await db.check_if_playlist_available(user_telegram_id, playlist_id, current_date)) is False:
        raise PlaylistNotAvailable
    return True


async def check_payment(user_telegram_id, db: Database):
    # TODO Здесь должна быть проверка, если юзер находится в блоклисте
    return True


def check_func_speed(func):
    """
    Декоратор для измерения скорости выполнения функции
    """
    async def wrapper(*args, **kwargs):
        print("Начинаем измерять скорость работы функции")
        start_time = datetime.now()
        await func(*args)
        print(f"Время выполнения: {datetime.now() - start_time}")
    return wrapper


async def format_invoice(chat_id, callback_data, provider_token):
    premium_info = callback_data["cur_action"]
    if premium_info == "buy_premium_2_mon":  # buy_premium_2_mon
        sub_price = 129
        sub_desc = "Премиум подписка 2 месяца"
        payload = '{"premium_days": 60}'

    elif premium_info == "buy_premium_4_mon":  # buy_premium_4_mon
        sub_price = 229
        sub_desc = "Премиум подписка 4 месяца"
        payload = '{"premium_days": 120}'
    elif premium_info == "buy_premium_6_mon":  # buy_premium_6_mon
        sub_price = 329
        sub_desc = "Премиум подписка 6 месяцев"
        payload = '{"premium_days": 180}'
    else:  # buy_premium_12_mon
        sub_price = 529
        sub_desc = "Премиум подписка 12 месяцев"
        payload = '{"premium_days": 365}'
    provider_data = {
        "receipt": {
            "items": [  # Элементы чека (товары/услуги)
                {
                    "description": sub_desc,
                    "quantity": "1",  # Количество# Название товара/услуги
                    "amount": {  # Стоимость и количество
                        "value": f"{sub_price}.00",  # Стоимость в копейках или центах (строка)
                        "currency": "RUB",  # Валюта (ISO код)
                    },
                    "vat_code": 1  # В документации без кавычек
                }
            ]
        }
    }
    invoice_parameters = {
        "chat_id": chat_id,
        "title": sub_desc,
        "description": "Оформление премиум подписки в @jammy_music_bot",
        "payload": payload,
        "provider_token": provider_token,
        "currency": "RUB",
        "prices": [types.LabeledPrice(sub_desc, sub_price * 100)],
        "need_email": True,
        "send_email_to_provider": True,
        "provider_data": provider_data
    }
    return invoice_parameters


async def get_audio_file_from_yt_video(yt_video: YouTube) -> (io.BytesIO, Stream):
    streams = await run_blocking_io(yt_video.__getattribute__,  "streams")
    audio_stream: Stream = await run_blocking_io(streams.get_audio_only)
    if audio_stream.filesize > 50000000:
        raise FileIsTooLarge
    audio_file = io.BytesIO()
    await run_blocking_io(audio_stream.stream_to_buffer, audio_file)
    await run_blocking_io(audio_file.seek, 0)
    return audio_file, audio_stream


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

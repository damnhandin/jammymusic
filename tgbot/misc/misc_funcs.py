import asyncio
import datetime
from datetime import datetime
from typing import Union

import aiogram
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InputMedia

from tgbot.misc.exceptions import PlaylistNotAvailable, PlaylistNotFound
from tgbot.models.db_utils import Database


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
            except:
                continue


async def catch_exception_if_playlist_is_not_available(target: Union[types.CallbackQuery, types.Message],
                                                       playlist_id: Union[int, str], db: Database,
                                                       current_date: datetime.date,
                                                       state: FSMContext) -> bool:
    if isinstance(playlist_id, str):
        playlist_id = int(playlist_id)
    try:
        if (await check_if_user_playlist_is_available(playlist_id,
                                                      db, target.from_user.id, current_date)) is not True:
            await target.answer("Плейлист недоступен")
            try:
                if isinstance(target, types.CallbackQuery):
                    await target.message.delete_reply_markup()
            except:
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


async def check_func_speed(func):
    """
    Декоратор для измерения скорости выполнения функции
    """
    def wrapper():
        print("Начинаем измерять скорость работы функции")
        start_time = datetime.now()
        func()
        print(f"Время выполнения: {datetime.now() - start_time} s.")
    return wrapper()

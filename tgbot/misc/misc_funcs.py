import datetime
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext

from tgbot.misc.exceptions import PlaylistNotAvailable, PlaylistNotFound
from tgbot.models.db_utils import Database


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

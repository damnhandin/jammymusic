import asyncio

import aiogram.dispatcher.filters
from aiogram import Dispatcher, types, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import MediaGroupFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.callback_datas import action_callback
from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def admin_start(message: Message):
    await message.reply("Hello, admin!")


async def admin_sending(message, state):
    await JammyMusicStates.admin_sending.set()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])
    msg_to_delete_reply = await message.answer("Теперь отправьте сообщение, которое хотите отправить",
                                               reply_markup=reply_markup)
    await state.update_data(msg_to_delete_reply=msg_to_delete_reply)


async def admin_get_media_group_to_sending(message):
    await message.answer("К сожалению бот не может отправлять медиагруппы")


async def admin_get_msg_to_sending(message: types.Message, state: FSMContext, db: Database):
    await state.reset_state(with_data=False)
    data = await state.get_data()
    msg_to_delete_reply: types.Message = data["msg_to_delete_reply"]
    try:
        await msg_to_delete_reply.delete_reply_markup()
    except:
        pass
    await state.reset_data()
    users = await db.select_all_users()
    print(users)
    count = 0
    for user in users:
        count += 1
        if count % 30 == 0:
            await asyncio.sleep(30)
        try:
            await message.send_copy(chat_id=user["telegram_id"])
        except aiogram.exceptions.BotBlocked:
            continue
        except aiogram.exceptions.ToMuchMessages:
            await asyncio.sleep(30)


async def get_my_id(message):
    await message.answer(f"<b>Ваш телеграм id:</b>\n{message.from_user.id}")


def register_admin(dp: Dispatcher):
    dp.register_message_handler(admin_start, AdminFilter(is_admin=True),
                                commands=["admin_check"], state="*")
    dp.register_message_handler(admin_get_msg_to_sending, AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=False),
                                state=JammyMusicStates.admin_sending)
    dp.register_message_handler(admin_get_media_group_to_sending, AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=True),
                                state=JammyMusicStates.admin_sending)
    dp.register_message_handler(get_my_id, commands=["get_my_id"], state="*")
    dp.register_message_handler(admin_sending, AdminFilter(is_admin=True), commands=["sending"])

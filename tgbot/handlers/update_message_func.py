import asyncio

from aiogram.dispatcher import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher, types
import aiogram.dispatcher.filters

from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.callback_datas import action_callback
from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def update_start(message: Message):
    await JammyMusicStates.update_sending.set()
    await message.reply("Привет админ, начать рассылку пользователям об обновлении?")
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(cur_action="update_sending"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])


async def send_update_message(message: types.Message, state: FSMContext, db: Database):
    await state.reset_state(with_data=False)
    update_text = "Дорогие пользователи @jammy_music_bot, \n " \
                  "у нас произошло обновление, нажмите /start, \n" \
                  "чтобы обновления успешно были произведены у вас"

    users = await db.select_all_users()
    count = 0
    for user in users:
        count += 1
        if count % 30 == 0:
            await asyncio.sleep(30)
        try:
            await message.bot.send_message(user, update_text)
        except aiogram.exceptions.BotBlocked:
            continue
        except aiogram.exceptions.ToMuchMessages:
            await asyncio.sleep(30)


def register_update(dp: Dispatcher):
    dp.register_message_handler(update_start, AdminFilter(is_admin=True),
                                commands=["update"], state="*")
    dp.register_message_handler(send_update_message, AdminFilter(is_admin=True),
                                commands=["update_sending"], state="*")

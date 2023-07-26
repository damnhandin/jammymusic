from aiogram import types, Dispatcher

from tgbot.filters.check_terms_filter import CheckUserFilter
from tgbot.keyboards.inline import accept_terms_keyboard
from tgbot.models.dataclasses.messages import BotMessages
from tgbot.models.db_utils import Database


async def check_user_callback_query_handler(cq: types.CallbackQuery):
    await cq.message.answer(BotMessages.messages["cond_terms_text"], reply_markup=accept_terms_keyboard,
                            disable_web_page_preview=False)


async def check_user_message_query_handler(message: types.Message):
    await message.answer(BotMessages.messages["cond_terms_text"], reply_markup=accept_terms_keyboard,
                         disable_web_page_preview=False)


def register_check_user_handlers(dp: Dispatcher, db: Database):
    dp.register_message_handler(check_user_message_query_handler, CheckUserFilter(db))
    dp.register_callback_query_handler(check_user_callback_query_handler, CheckUserFilter(db))

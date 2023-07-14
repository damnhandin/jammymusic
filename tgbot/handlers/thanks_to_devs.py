from aiogram import types, Dispatcher

from tgbot.keyboards.callback_datas import action_callback
from tgbot.models.db_utils import Database


async def thanks_to_devs_func(cq: types.CallbackQuery, db: Database):
    await db.add_user_to_thanks_to_devs_table(cq.from_user.id)
    await cq.message.answer("🙃")


def register_thanks_to_devs_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(thanks_to_devs_func, action_callback.filter(cur_action="thanks_to_devs"),
                                       state="*")

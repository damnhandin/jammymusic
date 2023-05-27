from aiogram import types, Dispatcher

from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.reply import start_keyboard
from tgbot.models.db_utils import Database


async def accept_conditional_terms(cq: types.CallbackQuery, db: Database):
    await db.user_accepted_cond_terms(cq.from_user.id)
    try:
        await cq.message.delete_reply_markup()
        await cq.answer("Лицензионное соглашение было принято")
    except:
        pass
    else:
        await cq.message.answer("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио",
                                reply_markup=start_keyboard)


def register_conditional_terms_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(accept_conditional_terms, action_callback.filter(
        cur_action="accept_conditional_terms"))

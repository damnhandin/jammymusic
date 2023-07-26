from aiogram import types, Dispatcher

from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import thanks_to_devs_keyboard
from tgbot.keyboards.reply import start_keyboard
from tgbot.models.db_utils import Database


async def accept_conditional_terms(cq: types.CallbackQuery, db: Database):
    await db.user_accepted_cond_terms(cq.from_user.id)
    try:
        await cq.message.delete()
    except Exception:
        pass
    else:
        await cq.message.answer("Пользовательское соглашение было принято, теперь можешь пользоваться ботом.",
                                reply_markup=start_keyboard)
        result = await db.gift_to_user_free_trial_premium(cq.from_user.id)
        if result is not None:
            await cq.message.answer("Пользовательское соглашение было принято. Теперь ты можешь пользоваться ботом. "
                                    "Кстати, лови подарок! Мы дарим тебе 14 дней премиум подписки!",
                                    reply_markup=thanks_to_devs_keyboard)


def register_conditional_terms_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(accept_conditional_terms, action_callback.filter(
        cur_action="accept_conditional_terms"))

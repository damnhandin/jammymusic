from datetime import datetime

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType

from tgbot.keyboards.inline import subscription_prices_keyboard
from tgbot.models.db_utils import Database


async def my_subscription_button_func(message: types.Message, db: Database):
    subscription_status = await db.check_subscription_is_valid(message.from_user.id, datetime.now())
    if subscription_status is False:
        await message.answer("У вас нет подписки", reply_markup=subscription_prices_keyboard)
        return
    else:
        subscription = await db.select_user_subscription(message.from_user.id)
        if subscription is False:
            await message.answer("Произошла ошибка, повторите попытку позже, либо обратитесь к администратору.",
                                 reply_markup=subscription_prices_keyboard)
            return
        text = f"У вас есть премиум подписка. Она активна до {subscription.get('subscription_date_end')}.\n" \
               f"Также вы можете приобрести еще подписку, если пожелаете."
        await message.answer(text, reply_markup=subscription_prices_keyboard)
    try:
        await message.delete()
    except Exception:
        pass

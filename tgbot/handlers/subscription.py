from aiogram import types, Dispatcher
from aiogram.types import ContentType

from tgbot.config import Config
from tgbot.keyboards.inline import subscription_prices_keyboard
from tgbot.models.db_utils import Database


async def subcription_check(message: types.Message, db: Database):
    is_signed = await db.check_user_subscription(message.from_user.id)
    if is_signed is False:
        await message.answer("У вас нет подписки", reply_markup=subscription_prices_keyboard)
        return
    else:
        date_end = await db.check_user_date_end(message.from_user.id)
        text = f"У вас есть премиум подписка. Она активна до {date_end}." \
               f"Также вы можете приобрести еще подписку, если пожелаете"
        await message.answer(text, reply_markup=subscription_prices_keyboard)
    try:
        await message.delete()
    except Exception:
        pass


def register_subcription(dp: Dispatcher):
    dp.register_message_handler(subcription_check, content_types=ContentType.TEXT)

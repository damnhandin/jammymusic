from aiogram import Dispatcher, types
from aiogram.types import ContentType

from datetime import datetime

from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def my_subscription_button_func(message: types.Message, db: Database, config):
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписка в @Jammymusic"

    subscription_status = await db.check_subscription_is_valid(message.from_user.id, datetime.now())
    if subscription_status is False:
        await message.bot.send_invoice(chat_id=message.chat.id,
                                       title=title_text,
                                       description=desc_text,
                                       payload='invoice',
                                       provider_token=config.tg_bot.payment_token,
                                       currency='RUB',
                                       prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])
        return
    else:
        subscription = await db.select_user_subscription(message.from_user.id)
        if subscription is False:
            await message.answer("Ваша подписка неактивна.")
            await message.bot.send_invoice(chat_id=message.chat.id,
                                           title=title_text,
                                           description=desc_text,
                                           payload='invoice',
                                           provider_token=config.tg_bot.payment_token,
                                           currency='RUB',
                                           prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])
            return
        text = f"У вас есть премиум подписка. Она активна до {subscription.get('subscription_date_end')}.\n" \
               f"Также вы можете приобрести еще подписку, если пожелаете."
        await message.answer(text)
        await message.bot.send_invoice(chat_id=message.chat.id,
                                       title=title_text,
                                       description=desc_text,
                                       payload='invoice',
                                       provider_token=config.tg_bot.payment_token,
                                       currency='RUB',
                                       prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])
    try:
        await message.delete()
    except Exception:
        pass


async def donate(message: types.Message, config):
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписка в @Jammymusic"
    await message.bot.send_invoice(chat_id=message.chat.id,
                                   title=title_text,
                                   description=desc_text,
                                   payload='invoice',
                                   provider_token=config.tg_bot.payment_token,
                                   currency='RUB',
                                   prices=[types.LabeledPrice('Премиум подписка', 69*100)])


async def get_unknown_content_to_donate(message: types.Message):
    await message.answer("Похоже, что вы хотели оплатить подписку, но мы получили от вас нечто иное. "
                         "Прошипите /start чтобы вернуться в главное меню.")


async def success_donate(message: types.Message, state):
    await state.reset_state()
    # тут надо функцию создать, чтобы в бд указывала, статус премиум, и дату конца подписки
    await message.answer(f'Платеж прошел успешно {message.successful_payment.order_info}')


def register_payment(dp: Dispatcher):
    dp.register_message_handler(success_donate, content_types=ContentType.SUCCESSFUL_PAYMENT,
                                state=JammyMusicStates.donate)
    dp.register_message_handler(get_unknown_content_to_donate, content_types=ContentType.ANY,
                                state=JammyMusicStates.donate)

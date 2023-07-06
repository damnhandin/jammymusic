from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, PreCheckoutQuery

from datetime import datetime

from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def my_subscription_button_func(message: types.Message, db: Database, config):
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписки в @jammy_music_bot"

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


async def check_payment(user_telegram_id, db: Database):
    # TODO Здесь должна быть проверка, если юзер находится в блоклисте
    return True


async def success_donate(query: PreCheckoutQuery, state: FSMContext, db: Database):
    await state.reset_state()
    if (await check_payment(query.from_user.id, db)) is False:
        error_text = "К сожалению, произошла ошибка, обратитесь к администратору, " \
                     "либо повторите позже"
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        return
    try:
        await db.add_new_subscription(query.from_user.id, 30)
    except:
        error_text = "К сожалению, произошла ошибка, обратитесь к администратору, " \
                     "либо повторите позже"
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        return
    await query.bot.answer_pre_checkout_query(query.id, True)


async def success_donate_msg(message: types.Message):
    await message.answer("Поздравляем, вы оформили подписку на нашего бота, приятного пользования!")


def register_payment(dp: Dispatcher):
    dp.register_pre_checkout_query_handler(success_donate,
                                           state="*")
    dp.register_message_handler(success_donate_msg, content_types=ContentType.SUCCESSFUL_PAYMENT, state="*")
    dp.register_message_handler(get_unknown_content_to_donate, content_types=ContentType.ANY,
                                state=JammyMusicStates.donate)

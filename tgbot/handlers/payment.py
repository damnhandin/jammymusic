import asyncpg
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

from datetime import datetime

from tgbot.handlers.user import run_blocking_io
from tgbot.keyboards.callback_datas import action_callback
from tgbot.misc.misc_funcs import check_payment
from tgbot.models.db_utils import Database


async def my_subscription_button_func(message: types.Message, db: Database, config):
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписки в @jammy_music_bot"
    currernt_date = datetime.now()

    subscription_status = await db.check_subscription_is_valid(message.from_user.id, currernt_date)
    if not subscription_status:
        await message.bot.send_invoice(chat_id=message.chat.id,
                                       title=title_text,
                                       description=desc_text,
                                       payload='invoice',
                                       provider_token=config.tg_bot.payment_token,
                                       currency='RUB',
                                       prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])
        return
    else:
        subscription = await db.select_first_user_subscription(message.from_user.id, currernt_date)
        if not subscription:
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

        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Мои подписки", callback_data=action_callback.new(
                cur_action="show_my_subscriptions"))]
        ])
        await message.answer(text, reply_markup=reply_markup)
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


async def success_donate(query: PreCheckoutQuery, state: FSMContext, db: Database):
    await state.reset_state()
    if (await check_payment(query.from_user.id, db)) is False:
        error_text = "К сожалению, произошла ошибка, обратитесь к администратору, " \
                     "либо повторите позже"
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        return

    await db.add_user_subscription_to_queue_then_activate_if_need(query.from_user.id, datetime.now(), 30)
    try:
        pass
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


async def show_my_subscriptions(cq: types.CallbackQuery, db: Database):
    subscriptions = await db.select_all_user_subscriptions(cq.from_user.id, datetime.now())
    if not subscriptions:
        await cq.answer("К сожалению, у вас нет премиума")
        return

    msg_text = "<b>Ваши активные подписки:</b>\n"
    msg_text = await run_blocking_io(format_subscriptions_to_msg_text, subscriptions, msg_text)
    await cq.message.answer(msg_text)


def format_subscriptions_to_msg_text(subscriptions: [asyncpg.Record], msg_text="") -> str:
    try:
        for num, sub in enumerate(subscriptions, start=1):
            msg_text += f'Подписка #{num}. {sub["subscription_date_start"]} - {sub["subscription_date_end"]}\n'
    except KeyError as exc:
        raise exc
    finally:
        return msg_text


def register_payment(dp: Dispatcher):
    dp.register_callback_query_handler(show_my_subscriptions,
                                       action_callback.filter(cur_action="show_my_subscriptions"), state="*")
    dp.register_pre_checkout_query_handler(success_donate,
                                           state="*")
    dp.register_message_handler(success_donate_msg, content_types=ContentType.SUCCESSFUL_PAYMENT, state="*")

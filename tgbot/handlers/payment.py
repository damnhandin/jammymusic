import json
import logging
from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

from datetime import datetime, timedelta

from aiogram.utils.exceptions import MessageCantBeEdited

from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import buy_subscription_keyboard_sub, buy_subscription_keyboard_unsub, \
    types_of_premium_keyboard
from tgbot.misc.misc_funcs import check_payment
from tgbot.models.db_utils import Database


async def my_subscription_button_func(target: Union[types.CallbackQuery, types.Message], db: Database):
    current_date = datetime.now()
    if isinstance(target, types.Message):
        message_bot_func = target.answer
    else:
        message_bot_func = target.message.edit_text

    subscription_status = await db.check_subscription_is_valid(target.from_user.id, current_date)
    if not subscription_status:
        await message_bot_func("У вас отсутствует премиум-подписка.", reply_markup=buy_subscription_keyboard_unsub)
        return
    else:
        subscription = await db.select_user_active_subscription(target.from_user.id, current_date)
        if not subscription:
            await message_bot_func("Ваша подписка неактивна.", reply_markup=buy_subscription_keyboard_unsub)
            return
        text = f"У вас есть премиум подписка.\n" \
               f"Также вы можете приобрести еще подписку, если пожелаете."
        await message_bot_func(text, reply_markup=buy_subscription_keyboard_sub)


async def success_donate(query: PreCheckoutQuery, state: FSMContext, db: Database):
    error_text = "К сожалению, произошла ошибка, обратитесь к администратору, " \
                 "либо повторите позже"
    await state.reset_state()
    if (await check_payment(query.from_user.id, db)) is False:
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        return

    try:
        invoice_payload = eval(query["invoice_payload"])
        premium_days = invoice_payload["premium_days"]
        await db.add_user_subscription_to_queue_then_activate_if_need(query.from_user.id, datetime.now(), premium_days)
    except Exception as exc:
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        raise exc
    else:
        await query.bot.answer_pre_checkout_query(query.id, True)


async def success_donate_msg(message: types.Message, db: Database):
    try:
        await db.add_payment_to_history(message.successful_payment.telegram_payment_charge_id,
                                        message.successful_payment.provider_payment_charge_id,
                                        message.from_user.id,
                                        int(message.successful_payment.total_amount/100))
    except Exception as exc:
        logging.info(f"Произошла ошибка во время добавления операции в историю!"
                     f"telegram_id={message.from_user.id}\n"
                     f"provider_payment_id={message.successful_payment.provider_payment_charge_id}")
        raise exc
    else:
        await message.answer("Поздравляем, вы оформили премиум-подписку на нашего бота, приятного пользования!")


async def show_my_subscriptions(cq: types.CallbackQuery, db: Database):
    subscription = await db.select_user_active_subscription(cq.from_user.id, datetime.now())
    sum_of_sub_days = await db.group_all_valid_subscriptions_in_queue(cq.from_user.id)
    # if not subscription and not subscriptions_in_queue:
    #     await cq.answer("К сожалению, у вас нет премиума")
    #     return

    if not subscription:
        msg_text = f"<b>В данный момент премиум не активирован.</b>"
    else:
        subscription_date_end = subscription['subscription_date_end']
        if sum_of_sub_days:
            subscription_date_end += timedelta(sum_of_sub_days)

        msg_text = f"<b>Активирован премиум:</b> {subscription['subscription_date_start']} - " \
                   f"{subscription_date_end}\n"
    # if sum_of_sub_days:
    #     msg_text += f"Доступно {sum_of_sub_days} дней премиума (активируется автоматически)"

    # msg_text = await run_blocking_io(format_subscriptions_to_msg_text, subscriptionn, msg_text)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад",
                              callback_data=action_callback.new(cur_action="back_to_sub_menu"))]
    ])
    await cq.message.edit_text(msg_text, reply_markup=reply_markup)


async def buy_subscription_button_func(cq: types.CallbackQuery, config):
    message_text = "<b>Виды премиума, которые вы можете приобрести:</b>\n" \
                   "2 месяца - 138 рублей\n" \
                   "3 месяца - 185 <s>207</s> рублей (-12% OFF)\n" \
                   "6 месяцев - 349 <s>414</s> рублей (-18.6% OFF)\n" \
                   "12 месяцев - 499 <s>828</s> рублей (-65.9% OFF)"
    try:
        await cq.message.edit_text(message_text, reply_markup=types_of_premium_keyboard)
    except MessageCantBeEdited:
        await cq.message.answer(message_text, reply_markup=types_of_premium_keyboard)


async def format_invoice(chat_id, callback_data, provider_token):
    # await cq.bot.send_invoice(chat_id=cq.from_user.id,
    #                           title=title_text,
    #                           description=desc_text,
    #                           payload='invoice',
    #                           provider_token=config.tg_bot.payment_token,
    #                           currency='RUB',
    #                           prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])
    premium_info = callback_data["cur_action"]
    if premium_info == "buy_premium_2_mon":  # buy_premium_2_mon
        sub_price = 129
        sub_desc = "Премиум подписка 2 месяца"
        payload = '{"premium_days": 60}'
    elif premium_info == "buy_premium_3_mon":  # buy_premium_3_mon
        sub_price = 229
        sub_desc = "Премиум подписка 3 месяца"
        payload = '{"premium_days": 90}'
    elif premium_info == "buy_premium_6_mon":  # buy_premium_6_mon
        sub_price = 329
        sub_desc = "Премиум подписка 6 месяцев"
        payload = '{"premium_days": 180}'
    else:  # buy_premium_12_mon
        sub_price = 529
        sub_desc = "Премиум подписка 12 месяцев"
        payload = '{"premium_days": 365}'
    provider_data = {
        "receipt": {
            "items": [  # Элементы чека (товары/услуги)
                {
                    "description": sub_desc,
                    "quantity": "1",  # Количество# Название товара/услуги
                    "amount": {  # Стоимость и количество
                        "value": f"{sub_price}.00",  # Стоимость в копейках или центах (строка)
                        "currency": "RUB",  # Валюта (ISO код)
                    },
                    "vat_code": 1  # В документации без кавычек
                }
            ]
        }
    }
    invoice_parameters = {
        "chat_id": chat_id,
        "title": sub_desc,
        "description": "Оформление премиум подписки в @jammy_music_bot",
        "payload": payload,
        "provider_token": provider_token,
        "currency": "RUB",
        "prices": [types.LabeledPrice(sub_desc, sub_price * 100)],
        "need_email": True,
        "send_email_to_provider": True,
        "provider_data": provider_data
    }
    return invoice_parameters


async def user_chose_premium_type_to_buy(cq: types.CallbackQuery, callback_data, config: Config):
    invoice_parameters = await format_invoice(cq.from_user.id, callback_data, config.tg_bot.payment_token)
    await cq.bot.send_invoice(**invoice_parameters)


def register_payment(dp: Dispatcher):
    dp.register_callback_query_handler(show_my_subscriptions,
                                       action_callback.filter(cur_action="show_my_subscriptions"), state="*")
    dp.register_callback_query_handler(my_subscription_button_func,
                                       action_callback.filter(cur_action="back_to_sub_menu"), state="*")
    dp.register_callback_query_handler(buy_subscription_button_func,
                                       action_callback.filter(cur_action="buy_subscription"), state="*")
    dp.register_callback_query_handler(user_chose_premium_type_to_buy,
                                       action_callback.filter(cur_action=[
                                           "buy_premium_2_mon",
                                           "buy_premium_3_mon",
                                           "buy_premium_6_mon",
                                           "buy_premium_12_mon"]))
    dp.register_pre_checkout_query_handler(success_donate,
                                           state="*")
    dp.register_message_handler(success_donate_msg, content_types=ContentType.SUCCESSFUL_PAYMENT, state="*")

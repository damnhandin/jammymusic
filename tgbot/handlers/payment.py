import logging
from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

from datetime import datetime, timedelta

from aiogram.utils.exceptions import MessageCantBeEdited
import aiogram.utils.markdown as fmt

from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import buy_subscription_keyboard_sub, buy_subscription_keyboard_unsub, \
    types_of_premium_keyboard
from tgbot.misc.misc_funcs import check_payment, format_invoice
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

    if not subscription:
        msg_text = f"{fmt.hbold('В данный момент премиум не активирован.')}"
    else:
        subscription_date_end = subscription['subscription_date_end']
        if sum_of_sub_days:
            subscription_date_end += timedelta(sum_of_sub_days)

        msg_text = f"{fmt.hbold('Активирован премиум:')} {subscription['subscription_date_start']} - " \
                   f"{subscription_date_end}\n"
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад",
                              callback_data=action_callback.new(cur_action="back_to_sub_menu"))]
    ])
    await cq.message.edit_text(msg_text, reply_markup=reply_markup)


async def buy_subscription_button_func(cq: types.CallbackQuery):

    message_text = f"{fmt.hbold('Виды премиума, которые вы можете приобрести:')}\n" \
                   "2 месяца — 129 рублей\n" \
                   "4 месяца — 229 <s>258</s> рублей (-12% OFF)\n" \
                   "6 месяцев — 329 <s>387</s> рублей (-15% OFF)\n" \
                   "12 месяцев — 529 <s>774</s> рублей (-32% OFF)"
    try:
        await cq.message.edit_text(message_text, reply_markup=types_of_premium_keyboard)
    except MessageCantBeEdited:
        await cq.message.answer(message_text, reply_markup=types_of_premium_keyboard)


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
                                           "buy_premium_4_mon",
                                           "buy_premium_6_mon",
                                           "buy_premium_12_mon"]))
    dp.register_pre_checkout_query_handler(success_donate,
                                           state="*")
    dp.register_message_handler(success_donate_msg, content_types=ContentType.SUCCESSFUL_PAYMENT, state="*")

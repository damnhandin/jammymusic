from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

from datetime import datetime, timedelta

from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import buy_subscription_keyboard_sub, buy_subscription_keyboard_unsub
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
    except Exception:
        error_text = "К сожалению, произошла ошибка, обратитесь к администратору, " \
                     "либо повторите позже"
        await query.bot.answer_pre_checkout_query(query.id, False, error_message=error_text)
        await query.bot.send_message(chat_id=query.from_user.id,
                                     text=error_text)
        return
    await query.bot.answer_pre_checkout_query(query.id, True)


async def success_donate_msg(message: types.Message):
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
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписки в @jammy_music_bot"
    await cq.bot.send_invoice(chat_id=cq.from_user.id,
                              title=title_text,
                              description=desc_text,
                              payload='invoice',
                              provider_token=config.tg_bot.payment_token,
                              currency='RUB',
                              prices=[types.LabeledPrice('Премиум подписка', 69 * 100)])


def register_payment(dp: Dispatcher):
    dp.register_callback_query_handler(show_my_subscriptions,
                                       action_callback.filter(cur_action="show_my_subscriptions"), state="*")
    dp.register_callback_query_handler(my_subscription_button_func,
                                       action_callback.filter(cur_action="back_to_sub_menu"), state="*")
    dp.register_callback_query_handler(buy_subscription_button_func,
                                       action_callback.filter(cur_action="buy_subscription"), state="*")
    dp.register_pre_checkout_query_handler(success_donate,
                                           state="*")
    dp.register_message_handler(success_donate_msg, content_types=ContentType.SUCCESSFUL_PAYMENT, state="*")

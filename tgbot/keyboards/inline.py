from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.callback_datas import action_callback

confirm_start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да, подтверждаю",
                          callback_data=action_callback.new(cur_action="confirm_to_start_menu"))],
    [InlineKeyboardButton(text="Нет, отменить переход",
                          callback_data=action_callback.new(cur_action="cancel_to_start_menu"))],
])
accept_terms_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Принять лиц. соглашение",
                                  callback_data=action_callback.new(cur_action="accept_conditional_terms"))]
        ])
subscription_prices_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить 1 месяц - 69 рублей",
                          callback_data=action_callback.new(cur_action="user_buy_one_month"))],
    '''[InlineKeyboardButton(text="Купить 2 месяца - 99 рублей",
                          callback_data=action_callback.new(cur_action="user_buy_two_months"))],'''
])

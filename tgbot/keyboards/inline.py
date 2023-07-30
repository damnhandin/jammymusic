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

my_subscriptions_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Мои подписки", callback_data=action_callback.new(
                cur_action="show_my_subscriptions"))]
        ])

buy_subscription_keyboard_unsub = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить подписку",
                          callback_data=action_callback.new(cur_action="buy_subscription"))]
])


buy_subscription_keyboard_sub = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить подписку",
                          callback_data=action_callback.new(cur_action="buy_subscription"))],
    [InlineKeyboardButton(text="Моя подписка", callback_data=action_callback.new(
        cur_action="show_my_subscriptions"))]
])

thanks_to_devs_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Вау, спасибо! ✨",
                          callback_data=action_callback.new(
                              cur_action="thanks_to_devs"
                          ))]
])


spam_sending_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(cur_action="spam_sending"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])
update_sending_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(cur_action="update_sending"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])
spam_sending_approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(cur_action="spam_sending_approve"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])
update_sending_approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅",
                              callback_data=action_callback.new(cur_action="update_sending_approve"))],
        [InlineKeyboardButton("❌",
                              callback_data=action_callback.new(cur_action="reset_state_delete_reply"))]
    ])

music_msg_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("Добавить в мои плейлисты",
                          callback_data=action_callback.new(cur_action="add_to_playlist"))]
])

types_of_premium_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("Купить 2 месяца",
                          callback_data=action_callback.new(cur_action="buy_premium_2_mon"))],
    [InlineKeyboardButton("Купить 3 месяца",
                          callback_data=action_callback.new(cur_action="buy_premium_3_mon"))],
    [InlineKeyboardButton("Купить 6 месяцев",
                          callback_data=action_callback.new(cur_action="buy_premium_6_mon"))],
    [InlineKeyboardButton("Купить 12 месяцев",
                          callback_data=action_callback.new(cur_action="buy_premium_12_mon"))],
    [InlineKeyboardButton(text="↩️ Назад",
                          callback_data=action_callback.new(cur_action="back_to_sub_menu"))]
])


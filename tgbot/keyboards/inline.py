from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.callback_datas import action_callback

confirm_start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да, подтверждаю",
                          callback_data=action_callback.new(cur_action="confirm_to_start_menu"))],
    [InlineKeyboardButton(text="Нет, отменить переход",
                          callback_data=action_callback.new(cur_action="cancel_to_start_menu"))],
])

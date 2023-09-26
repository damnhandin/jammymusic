from datetime import date as datetime_date
from typing import Union

from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware


class ActiveUsers(BaseMiddleware):
    """This middleware is for capturing media groups."""

    attendance_data: dict = {}

    async def on_pre_process_message(self, target: Union[types.Message, types.CallbackQuery], data: dict):
        user_id = target.from_user.id
        self.attendance_data[user_id] = datetime_date.today()


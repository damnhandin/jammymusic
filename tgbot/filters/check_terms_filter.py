import typing
from datetime import datetime

from aiogram import types
from aiogram.dispatcher.filters import BoundFilter

from tgbot.config import Config
from tgbot.models.db_utils import Database


class CheckUserFilter(BoundFilter):
    def __init__(self, db: Database):
        self.db = db

    async def check(self, obj: typing.Union[types.Message, types.CallbackQuery]):
        user = await self.db.initialize_new_user(obj.from_user.id, obj.from_user.full_name, obj.from_user.username,
                                                 datetime.now(), False)
        return user["accepted_terms"] is False



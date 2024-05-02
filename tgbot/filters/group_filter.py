import typing

from aiogram import types
from aiogram.dispatcher.filters import BoundFilter


class GroupFilter(BoundFilter):
    key = 'is_group'

    def __init__(self, is_group: typing.Optional[bool] = None):
        self.is_group = is_group

    async def check(self, obj: typing.Union[types.Message, types.CallbackQuery]):
        if isinstance(obj, types.CallbackQuery):
            msg = obj.message
        else:
            msg = obj
        return msg.chat.type != types.ChatType.PRIVATE




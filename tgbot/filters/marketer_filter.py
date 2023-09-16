import typing

from aiogram.dispatcher.filters import BoundFilter

from tgbot.config import Config


class MarketerFilter(BoundFilter):
    key = 'is_marketer'

    def __init__(self, is_marketer: typing.Optional[bool] = None):
        self.is_marketer = is_marketer

    async def check(self, obj):
        if self.is_marketer is None:
            return False
        config: Config = obj.bot.get('config')
        return (obj.from_user.id in config.tg_bot.marketer_ids) == self.is_marketer

from aiogram import Dispatcher
from aiogram.dispatcher.filters import CommandStart

from tgbot.filters.group_filter import GroupFilter


async def start_command_in_chat(msg):
    await msg.reply("Для поиска необходимо написать /jammy и указать название песни, например:\n"
                    "/jammy Milky Chance - Stolen Dance")
    return


def register_default_commands_in_group(dp: Dispatcher):
    dp.register_message_handler(start_command_in_chat,
                                CommandStart(),
                                GroupFilter(is_group=True))


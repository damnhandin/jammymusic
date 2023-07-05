import asyncio
from typing import Union

from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware


class AlbumMiddleware(BaseMiddleware):
    """This middleware is for capturing media groups."""

    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 1):
        """
        You can provide custom latency to make sure
        albums are handled properly in highload.
        """
        self.latency = latency
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return
        if not self.album_data.get(message.media_group_id):
            self.album_data[message.media_group_id] = [message]

        if message in self.album_data.get(message.media_group_id):
            await asyncio.sleep(self.latency)
            message.conf["is_last"] = True
            data["album"] = self.album_data[message.media_group_id]
        else:
            self.album_data[message.media_group_id].append(message)
            raise CancelHandler()

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        """Clean up after handling our album."""
        if message.media_group_id and message.conf.get("is_last"):
            del self.album_data[message.media_group_id]

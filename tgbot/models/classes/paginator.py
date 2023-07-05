from math import ceil
from typing import Union

from aiogram import Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.callback_datas import action_callback, edit_playlist_callback, playlist_callback, \
    playlist_navg_callback
from tgbot.models.db_utils import Database


class PlaylistPaginator:
    def __init__(self, limit_per_page=5, dp: Union[Dispatcher, None] = None):
        self.limit_per_page = limit_per_page
        self.dp: Dispatcher = dp

    async def create_playlist_keyboard(self, user_telegram_id, db: Database, cur_page=1, cur_mode="default",
                                       add_track_mode=False, edit_mode=False, check_cur_page=False):
        if type(cur_page) is not int:
            cur_page = int(cur_page)
        if not any([add_track_mode, edit_mode]):
            if cur_mode == "edit_mode":
                edit_mode = True
                add_track_mode = False
            elif cur_mode == "add_track_mode":
                edit_mode = False
                add_track_mode = True
            else:
                edit_mode = False
                add_track_mode = False

        if check_cur_page is True:
            cur_page = await self.__check_cur_page(user_telegram_id, db, cur_page)

        playlists = await db.select_user_playlists(user_telegram_id, self.limit_per_page,
                                                   (cur_page - 1) * self.limit_per_page)

        playlists_keyboard = await self._add_playlists_buttons(playlists, edit_mode=edit_mode,
                                                               cur_mode=cur_mode, cur_page=cur_page)
        await self._add_navigation_buttons(cur_page, cur_mode, keyboard=playlists_keyboard)
        await self._add_interaction_buttons(cur_page, cur_mode, keyboard=playlists_keyboard,
                                            add_track_mode=add_track_mode, edit_mode=edit_mode)

        return playlists_keyboard

    async def next_page_navigation(self, user_telegram_id: int, cur_page: int, cur_mode: str,
                                   db: Database, count_of_pages: int, add_track_mode: bool = False):
        if cur_page + 1 > count_of_pages:
            cur_page = 1
        else:
            cur_page += 1
        keyboard = await self.create_playlist_keyboard(user_telegram_id, db, cur_page=cur_page,
                                                       cur_mode=cur_mode,
                                                       add_track_mode=add_track_mode)
        return keyboard

    async def prev_page_navigation(self, user_telegram_id: int, cur_page: int, cur_mode: str,
                                   db: Database, count_of_pages: int, add_track_mode: bool = False):
        if cur_page - 1 < 1:
            cur_page = count_of_pages
        else:
            cur_page -= 1
        keyboard = await self.create_playlist_keyboard(user_telegram_id, db, cur_page=cur_page,
                                                       cur_mode=cur_mode,
                                                       add_track_mode=add_track_mode)
        return keyboard

    async def count_of_amount_pages_of_user_playlist(self, user_telegram_id, db: Database):
        count_of_pages = ceil(await db.count_of_user_playlists(user_telegram_id) / self.limit_per_page)
        if count_of_pages == 0:
            count_of_pages = 1
        return count_of_pages

    async def __check_cur_page(self, user_telegram_id, db: Database, cur_page):
        count_of_pages = await self.count_of_amount_pages_of_user_playlist(user_telegram_id, db)
        if cur_page > count_of_pages:
            cur_page = count_of_pages
        return cur_page

    @staticmethod
    async def _add_interaction_buttons(cur_page, cur_mode, keyboard=None, add_track_mode=False, edit_mode=False):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()

        keyboard.row(
            InlineKeyboardButton("🔹Создать", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                                      cur_mode=cur_mode,
                                                                                      cur_action="create_playlist")),
            InlineKeyboardButton("❌Отменить", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                                       cur_mode=cur_mode,
                                                                                       cur_action="cancel_playlist"))
            if edit_mode or add_track_mode else
            InlineKeyboardButton("🔸Изменить", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                                       cur_mode=cur_mode,
                                                                                       cur_action="edit_playlist"))
        )

    @staticmethod
    async def _add_navigation_buttons(cur_page, cur_mode, keyboard=None):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("◀️", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                                cur_mode=cur_mode,
                                                                                cur_action="prev_page")),
            InlineKeyboardButton("🔄", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                               cur_mode=cur_mode,
                                                                               cur_action="refresh")),
            InlineKeyboardButton("▶️", callback_data=playlist_navg_callback.new(cur_page=cur_page,
                                                                                cur_mode=cur_mode,
                                                                                cur_action="next_page"))
        )
        return keyboard

    @staticmethod
    async def _add_playlists_buttons(playlists, keyboard=None, edit_mode=False, cur_mode="default", cur_page=1):
        if keyboard is None:
            keyboard = InlineKeyboardMarkup()
        if edit_mode:
            callback_data = edit_playlist_callback
        else:
            callback_data = playlist_callback

        for playlist in playlists:
            keyboard.row(InlineKeyboardButton(playlist["playlist_title"],
                                              callback_data=callback_data.new(
                                                  playlist_id=playlist["playlist_id"],
                                                  cur_mode=cur_mode,
                                                  cur_page=cur_page
                                              )))
        return keyboard

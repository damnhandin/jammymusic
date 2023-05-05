from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.callback_datas import action_callback, playlist_callback
from tgbot.keyboards.inline import confirm_start_keyboard
from tgbot.keyboards.reply import start_keyboard
from tgbot.models.db_utils import Database


async def user_start_with_state(message):
    await message.answer("Вы уверены, что хотите перейти в главное меню?", reply_markup=confirm_start_keyboard)


async def user_confirm_start(cq, state):
    await state.reset_state(with_data=True)
    await cq.message.edit_text("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио",
                               reply_markup=start_keyboard)


async def delete_this_cq_message(cq: types.CallbackQuery):
    await cq.message.delete()


async def user_start(message: types.Message):
    await message.answer("Отправь мне название или ссылку на видео в ютубе и я тебе верну аудио",
                         reply_markup=start_keyboard)


class PlaylistPaginator:
    def __init__(self, db: Database, telegram_id, edit_mode=False, cur_page=1, limit_per_page=5):
        self.telegram_id = telegram_id
        self.cur_page = cur_page
        self.limit_per_page = limit_per_page
        self.edit_mode = edit_mode
        self.db = db

    async def create_playlist_preview_keyboard(self):
        playlists = await self.db.select_user_playlists(self.telegram_id, self.limit_per_page,
                                                        (self.cur_page - 1) * self.limit_per_page)
        playlists_keyboard = InlineKeyboardMarkup()
        for playlist in playlists:
            playlists_keyboard.row(InlineKeyboardButton(playlist["playlist_name"],
                                                        callback_data=playlist_callback.new(
                                                            playlist_id=playlist["playlist_id"])))
        playlists_keyboard.row(
            InlineKeyboardButton("◀️", callback_data=action_callback.new(cur_action="prev_page")),
            InlineKeyboardButton("🔄", callback_data=action_callback.new(cur_action="refresh")),
            InlineKeyboardButton("▶️", callback_data=action_callback.new(cur_action="next_page"))
        )
        playlists_keyboard.row(
            InlineKeyboardButton("🔹Создать", callback_data=action_callback.new(cur_action="create_playlist")),
            InlineKeyboardButton("❌Отменить", callback_data=action_callback.new(cur_action="cancel_edit_playlist"))
            if self.edit_mode else
            InlineKeyboardButton("🔸Изменить", callback_data=action_callback.new(cur_action="edit_playlist"))
        )
        return playlists_keyboard


async def my_plalists(message: types.Message, db: Database, state: FSMContext):
    playlist_paginator = PlaylistPaginator(db, message.from_user.id)
    reply_markup = await playlist_paginator.create_playlist_preview_keyboard()
    await state.update_data(playlist_paginator=playlist_paginator)
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer('<b>Ваши плейлисты:</b>', reply_markup=reply_markup)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, CommandStart())
    dp.register_message_handler(user_start_with_state, CommandStart(), state="*")
    dp.register_callback_query_handler(user_confirm_start, action_callback.filter(cur_action="confirm_to_start_menu"),
                                       state="*")
    dp.register_message_handler(my_plalists, Text("🎧 Мои плейлисты"))
    dp.register_callback_query_handler(delete_this_cq_message,
                                       action_callback.filter(cur_action="cancel_to_start_menu"),
                                       state="*")

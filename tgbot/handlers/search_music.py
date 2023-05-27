from json import loads

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils.exceptions import MessageIsTooLong
from youtubesearchpython import SearchVideos

from tgbot.config import Config
from tgbot.handlers.user import run_blocking_io
from tgbot.keyboards.callback_datas import video_callback
from tgbot.keyboards.inline import accept_terms_keyboard
from tgbot.models.db_utils import Database


async def search_music_func(mes: types.Message, db: Database, config: Config):
    is_accepted = await db.check_user_terms(mes.from_user.id)
    if is_accepted is False:
        await mes.answer(config.terms.cond_terms_text, reply_markup=accept_terms_keyboard)
        return
    try:
        await mes.delete()
    except Exception:
        pass
    # (self, keyword, offset = 1, mode = 'json', max_results = 20, language = 'en', region = 'US'
    search_results = (await run_blocking_io(
        SearchVideos, mes.text, 1, 'json', 5, 'ru-RU', 'RU'
    )).result()
    if not search_results:
        await mes.answer("Никаких совпадений по запросу.")
        return
    search_results_json = await run_blocking_io(loads, search_results)
    reply_markup = InlineKeyboardMarkup()
    for res in search_results_json["search_result"]:
        # self.id, self.link, self.title, self.channel, self.duration
        reply_markup.row(InlineKeyboardButton(f"{res['duration']} {res['title']}",
                                              callback_data=video_callback.new(video_id=res["id"])))
        await db.add_video(res["id"], res["link"], res["title"])

    answer = f'<b>Результаты по запросу</b>: {mes.text}'
    # keyboard = InlineKeyboard(*kb_list, row_width=1)
    try:
        await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
    except MessageIsTooLong:
        await mes.answer(f'<b>Результаты по вашему запросу</b>:', reply_markup=reply_markup)

def register_search_music(dp: Dispatcher):
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)


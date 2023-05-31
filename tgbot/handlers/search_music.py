from json import loads

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils.exceptions import MessageIsTooLong
from youtubesearchpython import VideosSearch
from ytmusicapi import YTMusic

from tgbot.config import Config
from tgbot.handlers.user import run_blocking_io, run_cpu_bound
from tgbot.keyboards.callback_datas import video_callback
from tgbot.keyboards.inline import accept_terms_keyboard
from tgbot.models.db_utils import Database


def filter_songs_without_correct_duration(video_searcher, searched_music=None):
    if searched_music is None:
        searched_music = list()
    songs_limit = 3
    while len(searched_music) < songs_limit:
        result = video_searcher.result().get("result")
        if not result:
            break
        for song in result:
            if song["duration"] != "LIVE" and song["duration"] is not None \
                    and ("hours" not in song["accessibility"]["duration"] and
                         "hour" not in song["accessibility"]["duration"]):
                searched_music.append(song)
            if len(searched_music) >= songs_limit:
                return searched_music
        video_searcher.next()
    return searched_music


def convert_search_results_to_reply_markup(search_results):
    reply_markup = InlineKeyboardMarkup()
    for res in search_results:
        if res.get("id"):
            video_id = res.get("id")
            cur_emoji = "📹"
            song_title = res.get("title")
        else:
            video_id = res.get("videoId")
            cur_emoji = "🎵"  # 🎶🎵
            song_artists = ", ".join([artist.get("name") for artist in res.get("artists")])
            if song_artists:
                song_title = f"{song_artists} - {res['title']}"
            else:
                song_title = res["title"]
        reply_markup.row(InlineKeyboardButton(f"{cur_emoji} {res['duration']} {song_title}",
                                              callback_data=video_callback.new(video_id=video_id)))
    return reply_markup


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
    yt: YTMusic = YTMusic()
    video_searcher = VideosSearch(mes.text, 5, 'ru-RU', 'RU')
    search_results = (await run_blocking_io(yt.search, mes.text, "songs", None, 3))[:6]
    search_results += await run_cpu_bound(filter_songs_without_correct_duration, video_searcher)
    if not search_results:
        await mes.answer("Никаких совпадений по запросу.")
        return
    reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup, search_results)

    answer = f'<b>Результаты по запросу</b>: {mes.text}'
    # keyboard = InlineKeyboard(*kb_list, row_width=1)
    try:
        await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
    except MessageIsTooLong:
        await mes.answer(f'<b>Результаты по вашему запросу</b>:', reply_markup=reply_markup)


def register_search_music(dp: Dispatcher):
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)


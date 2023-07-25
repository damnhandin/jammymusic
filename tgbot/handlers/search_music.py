from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType, InputFile
from aiogram.utils.exceptions import MessageIsTooLong
from pytube import YouTube, Stream
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch, Video, ResultMode, Playlist
from ytmusicapi import YTMusic

import io

from tgbot.handlers.user import run_blocking_io, run_cpu_bound
from tgbot.keyboards.callback_datas import video_callback, action_callback

import re

from tgbot.misc.misc_funcs import check_func_speed


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
            cur_emoji = "🎵"
            song_title = res.get("title")
        else:
            video_id = res.get("videoId")
            cur_emoji = "🎶"  # 🎶🎵
            song_artists = ", ".join([artist.get("name") for artist in res.get("artists")])
            if song_artists:
                song_title = f"{song_artists} - {res['title']}"
            else:
                song_title = res["title"]
        reply_markup.row(InlineKeyboardButton(f"{cur_emoji} {res['duration']} {song_title}",
                                              callback_data=video_callback.new(video_id=video_id)))
    return reply_markup


@check_func_speed
async def search_music_func(mes: types.Message):
    try:
    # Сначала идет проверка по видео гет, потом добавлю плейлист гет
        video = Video.get(mes.text, mode=ResultMode.dict, get_upload_date=True)
        video_id = video["id"]
        if video_id:
            yt_link = f"https://www.youtube.com/watch?v={video_id}"
            try:
                yt_video = YouTube(yt_link)
            except:
                yt_link = f"https://music.youtube.com/watch?v={video_id}"
                yt_video = YouTube(yt_link)
            if not yt_video:
                await mes.answer('Произошла ошибка!')
                return
            try:
                audio: Stream = yt_video.streams.get_audio_only()
            except AgeRestrictedError:
                return
            if audio.filesize > 50000000:
                await mes.answer('Произошла ошибка! Файл слишком большой, я не смогу его отправить')
                return
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("Добавить в мои плейлисты",
                                      callback_data=action_callback.new(cur_action="add_to_playlist"))]
            ])
            audio_file = io.BytesIO()
            await run_blocking_io(audio.stream_to_buffer, audio_file)
            await run_blocking_io(audio_file.seek, 0)
            await mes.answer_audio(InputFile(audio_file), title=audio.title,
                                   performer=yt_video.author if yt_video.author else None,
                                   reply_markup=reply_markup, caption='Больше музыки на @jammy_music_bot')
            return
    except:
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

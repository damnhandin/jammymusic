from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType, InputFile
from aiogram.utils.exceptions import MessageIsTooLong
from pytube import YouTube, Stream
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch, Video, ResultMode
from ytmusicapi import YTMusic

import io

from tgbot.handlers.user import run_blocking_io, run_cpu_bound
from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import music_msg_keyboard

from tgbot.misc.misc_funcs import convert_search_results_to_reply_markup, filter_songs_without_correct_duration


async def search_music_func(mes: types.Message):
    try:
        video = Video.get(mes.text, mode=ResultMode.dict, get_upload_date=True)
        video_id = video.get("id")
        if not video_id:
            raise Exception
        if video_id:
            yt_link = f"https://music.youtube.com/watch?v={video_id}"
            try:
                yt_video = YouTube(yt_link)
            except:
                yt_link = f"https://www.youtube.com/watch?v={video_id}"
                yt_video = YouTube(yt_link)
            if not yt_video:
                raise Exception
            else:
                await mes.answer("Ищу информацию по данному запросу!")
            try:
                # TODO: sync func
                audio: Stream = yt_video.streams.get_audio_only()
            except AgeRestrictedError:
                await mes.answer("Данная музыка ограничена по возрасту")
                return
            if audio.filesize > 50000000:
                await mes.answer('Произошла ошибка! Файл слишком большой, я не смогу его отправить')
                return
            audio_file = io.BytesIO()
            await run_blocking_io(audio.stream_to_buffer, audio_file)
            await run_blocking_io(audio_file.seek, 0)
            await mes.answer_audio(InputFile(audio_file), title=audio.title,
                                   performer=yt_video.author if yt_video.author else None,
                                   reply_markup=music_msg_keyboard, caption='Больше музыки на @jammy_music_bot')
            return
    except Exception:
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

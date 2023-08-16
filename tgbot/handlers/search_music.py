from aiogram import Dispatcher, types
from aiogram.types import ContentType, InputFile
from aiogram.utils.exceptions import MessageIsTooLong
import aiogram.utils.markdown as fmt
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch, Video, ResultMode
from ytmusicapi import YTMusic

from tgbot.keyboards.inline import music_msg_keyboard
from tgbot.misc.exceptions import FileIsTooLarge

from tgbot.misc.misc_funcs import convert_search_results_to_reply_markup, filter_songs_without_correct_duration, \
    get_audio_file_from_yt_video, run_blocking_io, run_cpu_bound


async def search_music_func(mes: types.Message):
    msg_text = fmt.text(mes.text)
    try:
        video = Video.get(msg_text, mode=ResultMode.dict, get_upload_date=True)
        video_id = video.get("id")
        if not video_id:
            raise Exception
        yt_link = f"https://music.youtube.com/watch?v={video_id}"
        try:
            yt_video = YouTube(yt_link)
        except Exception:
            yt_link = f"https://www.youtube.com/watch?v={video_id}"
            yt_video = YouTube(yt_link)
        if not yt_video:
            raise Exception
        else:
            await mes.answer("Ищу информацию по данному запросу!")
        try:
            audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
        except AgeRestrictedError:
            await mes.answer("Данная музыка ограничена по возрасту")
            return
        except FileIsTooLarge:
            await mes.answer('Файл слишком большой, я не смогу его отправить')
            return
        await mes.answer_audio(InputFile(audio_file), title=audio_stream.title,
                               performer=yt_video.author if yt_video.author else None,
                               reply_markup=music_msg_keyboard, caption='Больше музыки на @jammy_music_bot')
        return
    except Exception:
        yt: YTMusic = YTMusic("./oauth.json")
        video_searcher = VideosSearch(msg_text, 5, 'ru-RU', 'RU')
        search_results = (await run_blocking_io(yt.search, msg_text, "songs", None, 3))[:6]
        search_results += await run_cpu_bound(filter_songs_without_correct_duration, video_searcher)
        if not search_results:
            await mes.answer("Никаких совпадений по запросу.")
            return
        reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup, search_results)

        answer = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
        # keyboard = InlineKeyboard(*kb_list, row_width=1)
        try:
            await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
        except MessageIsTooLong:
            await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup)


def register_search_music(dp: Dispatcher):
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)

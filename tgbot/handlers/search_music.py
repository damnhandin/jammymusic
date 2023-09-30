from aiogram import Dispatcher, types
from aiogram.types import ContentType, InputFile, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageIsTooLong
import aiogram.utils.markdown as fmt
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch, Video, ResultMode
from yandex_music import ClientAsync
from tgbot.config import Config

from tgbot.keyboards.inline import music_msg_keyboard
from tgbot.misc.exceptions import FileIsTooLarge

from tgbot.misc.misc_funcs import convert_search_results_to_reply_markup, filter_songs_without_correct_duration, \
    get_audio_file_from_yt_video, run_cpu_bound, run_blocking_io, convert_music_api_search_res_to_reply_markup


async def search_music_func(mes: types.Message, config: Config):
    msg_text = fmt.text(mes.text)
    try:
        video = Video.get(msg_text, mode=ResultMode.dict, get_upload_date=True)
        video_id = video.get("id")
        if not video_id:
            raise Exception
        yt_link = f"https://music.youtube.com/watch?v={video_id}"
        try:
            yt_video = YouTube(yt_link, use_oauth=True)
        except Exception:
            yt_link = f"https://www.youtube.com/watch?v={video_id}"
            yt_video = YouTube(yt_link, use_oauth=True)
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
        video_searcher = await run_blocking_io(VideosSearch, msg_text, 4, 'ru-RU', 'RU')
        search_results = await run_cpu_bound(filter_songs_without_correct_duration, video_searcher)
        if not search_results:
            await mes.answer("Никаких совпадений по запросу.")
            return
        reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup, search_results)
        # answer = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
        # try:
        #     await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
        # except MessageIsTooLong:
        #     await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup)
        ####################################################################
        #client = await ClientAsync(f'{config.tg_bot.y_token}').init() dont work
        client = await ClientAsync('y0_AgAAAABw7WXsAAG8XgAAAADtKMqC_mWtBnYQSyOr5luJ142zrDOcm6o').init()

        ya_search = await client.search(mes.text)
        ya_tracks = ya_search.tracks.results[:4]
        if ya_tracks:
            ya_search_res_reply_markup = await run_cpu_bound(convert_music_api_search_res_to_reply_markup, ya_tracks)
            search_results_reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup,
                                                              search_results[:4])
            ya_buttons = ya_search_res_reply_markup.inline_keyboard
            search_buttons = search_results_reply_markup.inline_keyboard
            combined_buttons = ya_buttons + search_buttons

            reply_markup = InlineKeyboardMarkup(inline_keyboard=combined_buttons)
        else:
            reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup, search_results)
        answer = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
        try:
            await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
        except MessageIsTooLong:
            await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup)


def register_search_music(dp: Dispatcher):
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)

import yandex_music
from aiogram import Dispatcher, types
from aiogram.types import ContentType, InputFile, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageIsTooLong
import aiogram.utils.markdown as fmt
from pytube.exceptions import AgeRestrictedError
from youtubesearchpython import VideosSearch

from tgbot.config import Config
from tgbot.keyboards.inline import music_msg_keyboard
from tgbot.misc.exceptions import FileIsTooLarge

from tgbot.misc.misc_funcs import convert_search_results_to_reply_markup, filter_songs_without_correct_duration, \
    get_audio_file_from_yt_video, run_cpu_bound, run_blocking_io, convert_music_api_search_res_to_reply_markup, \
    get_yt_video_by_link, convert_search_divided_results_to_reply_markup


async def get_audios_from_video_searcher(search_pattern, videos_limit):
    video_searcher = await run_blocking_io(VideosSearch, search_pattern, videos_limit, 'ru-RU', 'RU')
    search_results = await run_cpu_bound(filter_songs_without_correct_duration, video_searcher, None, videos_limit)
    return search_results


async def search_music_func(mes: types.Message, config: Config, ya_music):
    msg_text = fmt.text(mes.text)
    try:
        yt_video = await get_yt_video_by_link(mes.text)
        if not yt_video:
            raise Exception
        else:
            await mes.answer("Ищу информацию по данному запросу!")
        audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
        await mes.answer_audio(InputFile(audio_file), title=audio_stream.title,
                               performer=yt_video.author if yt_video.author else None,
                               reply_markup=music_msg_keyboard, caption='Больше музыки на @jammy_music_bot')
        return
    except AgeRestrictedError:
        await mes.answer("Данная музыка ограничена по возрасту")
        return
    except FileIsTooLarge:
        await mes.answer('Файл слишком большой, я не смогу его отправить')
        return
    # Если возникает ошибка, значит текст это не ссылка на видео
    except Exception:
        pass
    songs_limit = 4
    yt_search_results = await get_audios_from_video_searcher(mes.text, songs_limit)
    if not yt_search_results:
        songs_limit = 8
    # if yt_search_results:
    #     reply_markup = await run_cpu_bound(convert_search_results_to_reply_markup, yt_search_results)
    # else:
    #     songs_limit = 8
    #     reply_markup = InlineKeyboardMarkup()
    ya_music: yandex_music.ClientAsync
    try:
        ya_search_results = (await ya_music.search(text=mes.text))
        ya_search_results = ya_search_results.tracks.results
    except:
        ya_search_results = []

    if ya_search_results and yt_search_results:
        ya_search_results = ya_search_results[:songs_limit]
    elif not ya_search_results and yt_search_results:
        yt_search_results = await get_audios_from_video_searcher(mes.text, songs_limit)
    elif ya_search_results and not yt_search_results:
        # TODO slice do async
        ya_search_results = ya_search_results[:songs_limit]

    if not yt_search_results and not ya_search_results:
        await mes.answer("Никаких совпадений по запросу.")
        return
    reply_markup = await run_cpu_bound(convert_search_divided_results_to_reply_markup,
                                       ya_search_results, yt_search_results)
    answer_text = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
    try:
        await mes.answer(answer_text, reply_markup=reply_markup, disable_web_page_preview=False)
    except MessageIsTooLong:
        await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup,
                         disable_web_page_preview=False)

    # answer = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
    # try:
    #     await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
    # except MessageIsTooLong:
    #     await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup)
    ####################################################################
    #client = await ClientAsync(f'{config.tg_bot.y_token}').init() dont work


def register_search_music(dp: Dispatcher):
    dp.register_message_handler(search_music_func, content_types=ContentType.TEXT)

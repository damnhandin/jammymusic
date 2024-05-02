from io import BytesIO

import yandex_music
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import ContentType, InputFile
from pytube.exceptions import AgeRestrictedError

from tgbot.filters.group_filter import GroupFilter
from tgbot.handlers.search_music import get_audios_from_video_searcher
from tgbot.misc.exceptions import FileIsTooLarge
from tgbot.misc.misc_funcs import get_yt_video_by_link, get_audio_file_from_yt_video, get_yt_video_by_video_id, \
    format_song_artists_from_ya_music


async def search_music_chat(msg: types.Message, ya_music):
    msg_text = msg.get_args()
    if not msg_text:
        await msg.reply("Для поиска необходимо указать название песни, например:\n"
                        "/jammy Milky Chance - Stolen Dance")
        return
    await msg.reply("Ищу информацию по данному запросу!")
    try:
        yt_video = await get_yt_video_by_link(msg_text)
        if not yt_video:
            raise Exception
        audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
        await msg.reply_audio(InputFile(audio_file), title=audio_stream.title,
                              performer=yt_video.author if yt_video.author else None)
        return
    except AgeRestrictedError:
        await msg.reply("Данная музыка ограничена по возрасту")
        return
    except FileIsTooLarge:
        await msg.reply('Файл слишком большой, я не смогу его отправить')
        return
    # Если возникает ошибка, значит текст это не ссылка на видео
    except Exception:
        pass
    songs_limit = 1
    ya_music: yandex_music.ClientAsync
    song_title = None
    song_performer = None
    try:
        search_result = (await ya_music.search(text=msg_text))
        search_result = search_result.tracks.results[0]
        audio_file = BytesIO(await search_result.download_bytes_async())
        song_title = search_result.title
        song_performer = await format_song_artists_from_ya_music(search_result)
    except Exception as exc:
        audio_file = None

    try:
        if not audio_file:
            search_result = await get_audios_from_video_searcher(msg_text, songs_limit)
            yt_video_id = search_result[0]["id"]
            yt_video = await get_yt_video_by_video_id(yt_video_id)
            audio_file, audio_stream = await get_audio_file_from_yt_video(yt_video)
            song_title = audio_stream.title
            song_performer = yt_video.author if yt_video.author else None
        if audio_file:
            await msg.reply_audio(InputFile(audio_file), title=song_title,
                                  performer=song_performer)
        else:
            raise Exception
    except AgeRestrictedError:
        await msg.reply("Данная музыка ограничена по возрасту")
        return
    except FileIsTooLarge:
        await msg.reply('Файл слишком большой, я не смогу его отправить')
        return
    except:
        await msg.reply("Никаких совпадений по запросу.")
        return




    # answer = f'{fmt.hbold("Результаты по запросу")}: {fmt.hcode(msg_text)}'
    # try:
    #     await mes.answer(answer, reply_markup=reply_markup, disable_web_page_preview=False)
    # except MessageIsTooLong:
    #     await mes.answer(f'{fmt.hbold("Результаты по вашему запросу:")}', reply_markup=reply_markup)
    ####################################################################
    # client = await ClientAsync(f'{config.tg_bot.y_token}').init() dont work


async def get_unknown_content(msg):
    pass


async def get_cq_in_group(cq):
    pass


def register_search_music_in_group(dp: Dispatcher):
    dp.register_message_handler(search_music_chat, GroupFilter(is_group=True), Command("jammy",
                                                                                       prefixes="!/"),
                                content_types=ContentType.TEXT)
    dp.register_message_handler(get_unknown_content, GroupFilter(is_group=True), content_types=ContentType.ANY)
    dp.register_callback_query_handler(get_cq_in_group, GroupFilter(is_group=True))

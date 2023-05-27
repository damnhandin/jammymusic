from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType
from shazamio.exceptions import FailedDecodeJson

from tgbot.misc.exceptions import RelatedSongsWasNotFound
from tgbot.misc.states import JammyMusicStates

from shazamio import Shazam


async def similar_songs_search(message: types.Message):
    await JammyMusicStates.shazam_recomendation.set()
    await message.answer(
        "Отправь мне имя исполнителя и название трека (например Моргенштерн aristocrat), а я попробую "
        "тебе посоветовать похожее")


async def parse_all_related_tracks_to_text(tracks, shazam: Shazam) -> str:
    all_related_songs = ""
    related_songs_flag = False
    for track in tracks:
        try:
            related_songs = (await shazam.related_tracks(track_id=track["actions"][0]["id"], limit=5))["tracks"]
            if not related_songs_flag and related_songs:
                related_songs_flag = True
            for related_song in related_songs:
                all_related_songs += f"{related_song['subtitle']} - {related_song['title']}\n"
        except (KeyError, FailedDecodeJson):
            continue
    if not related_songs_flag:
        raise RelatedSongsWasNotFound
    return all_related_songs


async def shazam_recommendation_search(message: types.Message, state):
    await state.reset_state()
    shazam = Shazam()
    try:
        tracks = (await shazam.search_track(query=message.text, limit=5)).get("tracks").get("hits")
        if tracks:
            text_message = "<b>Похожие треки:</b>\n"
            text_message += await parse_all_related_tracks_to_text(tracks, shazam)
            text_message += "Больше музыки на @jammy_music_bot"
            await message.answer(text_message)
        else:
            await message.answer("Я не знаю, что тебе посоветовать")
    except (RelatedSongsWasNotFound, KeyError, AttributeError):
        await message.answer("Я не знаю, что тебе посоветовать")
        return


async def get_unknown_content_to_find_similar(message: types.Message):
    await message.answer("Мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")


def register_similar_songs_search(dp: Dispatcher):
    dp.register_message_handler(similar_songs_search, Text("🎼 Найти похожие треки"),
                                state="*")
    dp.register_message_handler(shazam_recommendation_search, content_types=ContentType.TEXT,
                                state=JammyMusicStates.shazam_recomendation)
    dp.register_message_handler(get_unknown_content_to_find_similar, content_types=ContentType.ANY,
                                state=JammyMusicStates.shazam_recomendation)

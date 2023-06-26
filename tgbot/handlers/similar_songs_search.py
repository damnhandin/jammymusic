from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType
from lyricsgenius import genius
from shazamio.exceptions import FailedDecodeJson
from ytmusicapi import YTMusic

from tgbot.config import Config
from tgbot.misc.exceptions import RelatedSongsWasNotFound
from tgbot.misc.states import JammyMusicStates

from shazamio import Shazam


async def similar_songs_search(message: types.Message):
    await JammyMusicStates.shazam_recomendation.set()
    await message.answer(
        "Отправь мне имя исполнителя и название трека (например Sting - Shape of my heart), а я попробую "
        "тебе посоветовать похожее")


async def parse_all_related_tracks_to_text_from_yt(tracks, shazam: Shazam) -> str:
    all_related_songs = ""
    related_songs_flag = False
    # end_index = len(tracks)
    # if end_index > 5:
    #     end_index = 5
    end_index = 1
    for i in range(end_index):
        track = tracks[i]
        song_artists = ", ".join([artist.get("name") for artist in track.get("artists")])
        if song_artists:
            song_title = f"{song_artists} - {track['title']}"
        else:
            song_title = track["title"]
        try:
            shazam_song = await shazam.search_track(song_title, limit=1)
            related_songs = await shazam.related_tracks(shazam_song["tracks"]["hits"][0]["key"], limit=8)
            related_songs = related_songs["tracks"]
        except KeyError:
            continue
        for related_song in related_songs:
            if related_songs_flag is False:
                related_songs_flag = True
            all_related_songs += f"<code>{related_song['subtitle']} - {related_song['title']}</code>\n\n"
    if related_songs_flag is False:
        raise RelatedSongsWasNotFound

    return all_related_songs


async def parse_all_related_tracks_to_text(tracks, shazam: Shazam) -> str:
    all_related_songs = ""
    related_songs_flag = False
    counter = 0
    for track in tracks:
        try:
            related_songs = (await shazam.related_tracks(track_id=track["key"], limit=5))["tracks"]
            if not related_songs_flag and related_songs:
                related_songs_flag = True
            for related_song in related_songs:
                all_related_songs += f"{related_song['subtitle']} - {related_song['title']}\n"
        except (KeyError, FailedDecodeJson):
            continue
        else:
            counter += 1
    if not related_songs_flag:
        raise RelatedSongsWasNotFound
    return all_related_songs


async def shazam_recommendation_search(message: types.Message, state, config: Config):
    await state.reset_state()
    # shazam = Shazam(language="ru", endpoint_country="RU")
    shazam = Shazam()
    try:
        # tracks = (await shazam.search_track(query=message.text, limit=5))
        # tracks = tracks.get("tracks").get("hits")
        tracks = YTMusic().search(query=message.text, filter="songs", limit=1)

        if tracks:
            text_message = "<b>Похожие треки:</b>\n"
            # text_message += await parse_all_related_tracks_to_text(tracks, shazam)
            text_message += await parse_all_related_tracks_to_text_from_yt(tracks, shazam)
            text_message += "Больше музыки на @jammy_music_bot"
            await message.answer(text_message)
        else:
            await message.answer("Я не знаю, что тебе посоветовать")

    except (RelatedSongsWasNotFound, KeyError, AttributeError) as exc:
        await message.answer("Я не знаю, что тебе посоветовать")
        return


async def get_unknown_content_to_find_similar(message: types.Message):
    await message.answer("Мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")


def register_similar_songs_search(dp: Dispatcher):
    dp.register_message_handler(shazam_recommendation_search, content_types=ContentType.TEXT,
                                state=JammyMusicStates.shazam_recomendation)
    dp.register_message_handler(get_unknown_content_to_find_similar, content_types=ContentType.ANY,
                                state=JammyMusicStates.shazam_recomendation)

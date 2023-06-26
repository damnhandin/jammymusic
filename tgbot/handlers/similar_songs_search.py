from aiogram import types, Dispatcher
from aiogram.types import ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from ytmusicapi import YTMusic

from tgbot.config import Config
from tgbot.handlers.search_music import convert_search_results_to_reply_markup
from tgbot.keyboards.callback_datas import video_callback
from tgbot.misc.exceptions import RelatedSongsWasNotFound
from tgbot.misc.states import JammyMusicStates

from shazamio import Shazam


async def similar_songs_search(message: types.Message):
    await JammyMusicStates.shazam_recomendation.set()
    await message.answer(
        "Отправь мне имя исполнителя и название трека (например Sting - Shape of my heart), а я попробую "
        "тебе посоветовать похожее")


async def parse_all_related_tracks_to_list_from_yt_music(tracks, shazam: Shazam) -> list:
    all_related_songs = []
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
            all_related_songs += related_songs
        except KeyError:
            continue
    return all_related_songs


async def format_all_related_tracks_to_text_from_shazam(related_songs) -> str:
    all_related_songs = ""
    for num, related_song in enumerate(related_songs, start=1):
        print(related_song)
        all_related_songs += f"{num}) <code>{related_song['subtitle']} - {related_song['title']}</code>\n\n"

    return all_related_songs


# async def parse_all_related_tracks_to_text(tracks, shazam: Shazam) -> str:
#     all_related_songs = ""
#     related_songs = await find_all_related_tracks_for_songs(tracks, shazam)
#     for related_song in related_songs:
#         try:
#             all_related_songs += f"{related_song['subtitle']} - {related_song['title']}\n"
#         except KeyError:
#             continue
#     return all_related_songs


async def convert_yt_songs_to_enumerated_inline_buttons(yt_songs) -> InlineKeyboardMarkup:
    reply_markup = InlineKeyboardMarkup(row_width=4)
    for num, song in enumerate(yt_songs, start=1):
        video_id = song.get("id") or song.get("videoId")
        reply_markup.insert(InlineKeyboardButton(text=str(num),
                                                 callback_data=video_callback.new(
                                                     video_id=video_id)))
    return reply_markup


async def parse_all_related_tracks_to_inline_buttons(related_tracks) -> types.InlineKeyboardMarkup:
    reply_markup = convert_search_results_to_reply_markup(related_tracks)

    return reply_markup


async def find_all_youtube_songs_from_list(songs):
    yt_songs = []
    yt_music = YTMusic()
    for song in songs:
        try:
            yt_songs.append(
                yt_music.search(f"{song.get('subtitle')} - {song.get('title')}", filter="songs", limit=1)[0])
        except (ValueError, KeyError):
            continue
    print(yt_songs)
    return yt_songs


async def shazam_recommendation_search(message: types.Message, state, config: Config):
    await state.reset_state()
    # shazam = Shazam(language="ru", endpoint_country="RU")
    shazam = Shazam()
    try:
        tracks = YTMusic().search(query=message.text, filter="songs", limit=1)
        if not tracks:
            raise RelatedSongsWasNotFound
        related_tracks_shazam = await parse_all_related_tracks_to_list_from_yt_music(tracks, shazam)
        if not related_tracks_shazam:
            raise RelatedSongsWasNotFound
        related_tracks_yt_music = await find_all_youtube_songs_from_list(related_tracks_shazam)
        if not related_tracks_yt_music:
            raise RelatedSongsWasNotFound
        reply_markup = await convert_yt_songs_to_enumerated_inline_buttons(related_tracks_yt_music)
        text_message = "<b>Похожие треки:</b>\n"
        text_message += await format_all_related_tracks_to_text_from_shazam(related_tracks_shazam)
        text_message += "Больше музыки на @jammy_music_bot"
        await message.answer(text_message, reply_markup=reply_markup)

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

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType

from tgbot.misc.states import JammyMusicStates

from shazamio import Shazam


async def similar_songs_search(message: types.Message):
    await JammyMusicStates.shazam_recomendation.set()
    await message.answer("Отправь мне имя исполнителя и название трека (например Моргенштерн aristocrat), а я попробую "
                     "тебе посоветовать похожее")


async def shazam_recomendation_search(message: types.Message, state):
    await state.reset_state()
    shazam = Shazam()
    try:
        tracks = await shazam.search_track(query=message.text, limit=5)
        print(tracks)
        list = {}
        if tracks:
            count_of_finded_songs = len(tracks['tracks']['hits'])
            for i in range(count_of_finded_songs):
                info = tracks['tracks']['hits'][i]['heading']
                id = int(tracks['tracks']['hits'][i]['actions'][0]['id'])
            try:
                related = await shazam.related_tracks(track_id=id, limit=10)
                tracks = []
                for i in range(10):
                    tracks.append(related['tracks'][i]['subtitle'] + " - " + related['tracks'][i]['title'])
                s = '\n'.join(tracks)
                await message.answer("Похожие треки:" + "\n" + s + "\n" + "Больше музыки на @jammy_music_bot")
            except Exception:
                await message.answer("Я не знаю, что тебе посоветовать")
        else:
            await message.answer("Я не знаю, что тебе посоветовать")
    except Exception:
        await message.answer("Я не знаю, что тебе посоветовать")


async def get_unknown_content_to_find_similar(message: types.Message):
    await message.answer("Мы получили от вас неизвестный формат файла, "
                         "пожалуйста, убедитесь в том, что вы действительно отправили только текст.")


def register_similar_songs_search(dp: Dispatcher):
    dp.register_message_handler(similar_songs_search, Text("🎼 Найти похожие треки"))
    dp.register_message_handler(similar_songs_search, content_types=ContentType.TEXT,
                                state=JammyMusicStates.shazam_recomendation)
    dp.register_message_handler(get_unknown_content_to_find_similar, content_types=ContentType.ANY,
                                state=JammyMusicStates.shazam_recomendation)

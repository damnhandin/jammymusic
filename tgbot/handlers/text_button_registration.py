from aiogram import Dispatcher
from aiogram.dispatcher.filters import Text

from tgbot.handlers.add_own_song import add_own_song_func
from tgbot.handlers.find_song import find_song_func
from tgbot.handlers.find_song_by_words import find_song_by_words
from tgbot.handlers.find_song_lyrics import find_lyrics
from tgbot.handlers.shazam import shazam_start_func
from tgbot.handlers.similar_songs_search import similar_songs_search
from tgbot.handlers.subscription import my_subscription_button_func

from tgbot.handlers.user import my_playlists


def text_button_registration(dp: Dispatcher):
    dp.register_message_handler(my_playlists, Text("🎧 Мои плейлисты"), state="*")
    dp.register_message_handler(find_song_func, Text("🔍 Найти музыку"),
                                state="*")
    dp.register_message_handler(find_song_by_words, Text("🎵 Найти песню по словам"),
                                state="*")
    dp.register_message_handler(find_lyrics, Text("📄 Найти текст песни"),
                                state="*")
    dp.register_message_handler(shazam_start_func, Text("🎙 Shazam"),
                                state="*")
    dp.register_message_handler(similar_songs_search, Text("🎼 Найти похожие треки"),
                                state="*")
    dp.register_message_handler(add_own_song_func, Text("😎 Добавить свой трек"),
                                state="*")
    dp.register_message_handler(my_subscription_button_func, Text("💎 Моя подписка"),
                                state="*")

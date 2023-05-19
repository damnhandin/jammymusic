from aiogram.dispatcher.filters.state import StatesGroup, State


class JammyMusicStates(StatesGroup):
    get_playlist_title = State()
    get_new_playlist_title = State()
    add_music_to_playlist = State()
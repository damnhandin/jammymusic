from aiogram.dispatcher.filters.state import StatesGroup, State


class JammyMusicStates(StatesGroup):
    get_playlist_title = State()

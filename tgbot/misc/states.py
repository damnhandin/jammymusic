from aiogram.dispatcher.filters.state import StatesGroup, State


class JammyMusicStates(StatesGroup):
    get_playlist_title = State()
    get_new_playlist_title = State()
    add_music_to_playlist = State()
    get_number_of_song_to_delete = State()
    add_own_song = State()
    find_music_by_words = State()
    find_lyrics = State()
    shazam_recomendation = State()

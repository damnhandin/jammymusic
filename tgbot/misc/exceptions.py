class PlaylistNotFound(BaseException):
    pass


class PlaylistNotAvailable(BaseException):
    pass


class SongNotFound(BaseException):
    pass


class LimitTracksInPlaylist(Exception):
    pass


class WrongSongNumber(Exception):
    pass


class RelatedSongsWasNotFound(Exception):
    pass


class FileIsTooLarge(Exception):
    pass

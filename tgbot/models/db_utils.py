from typing import Union


import asyncpg
from asyncpg import Pool, Connection, UniqueViolationError

from tgbot.config import load_config
from tgbot.misc.exceptions import PlaylistNotFound, LimitTracksInPlaylist

config = load_config(".env")


class Database:

    def __init__(self):
        self.pool: Union[Pool, None] = None

    async def create(self):
        self.pool = await asyncpg.create_pool(
            user=config.db.user,
            password=config.db.password,
            host=config.db.host,
            database=config.db.database
        )

    async def execute(self, command, *args,
                      fetch: bool = False,
                      fetchval: bool = False,
                      fetchrow: bool = False,
                      execute: bool = False
                      ):
        async with self.pool.acquire() as connection:
            connection: Connection
            async with connection.transaction():
                if fetch:
                    result = await connection.fetch(command, *args)
                elif fetchval:
                    result = await connection.fetchval(command, *args)
                elif fetchrow:
                    result = await connection.fetchrow(command, *args)
                elif execute:
                    result = await connection.execute(command, *args)
            return result

    async def create_table_users(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        full_name VARCHAR(128) NOT NULL,
        username VARCHAR(36) NULL,
        telegram_id BIGINT NOT NULL UNIQUE,
        registration_date DATE NOT NULL,
        accepted_terms BOOL NOT NULL
        );
        """

        await self.execute(sql, execute=True)

    async def create_table_videos(self):
        # self.id, self.link, self.title, self.channel, self.duration
        sql = """
            CREATE TABLE IF NOT EXISTS videos(
            p_id SERIAL PRIMARY KEY,
            video_id VARCHAR(50) UNIQUE NOT NULL,
            link VARCHAR(100) NOT NULL,
            title VARCHAR(300) NOT NULL
            );
        """
        await self.execute(sql, execute=True)

    async def create_table_user_playlists(self):
        sql = """
        CREATE TABLE IF NOT EXISTS user_playlists (
        playlist_id SERIAL PRIMARY KEY,
        user_telegram_id BIGINT NOT NULL,
        playlist_title VARCHAR(50) NOT NULL
        );
        """
        await self.execute(sql, execute=True)

    async def create_table_tracks(self):
        sql = """
        CREATE TABLE IF NOT EXISTS tracks (
            track_id SERIAL PRIMARY KEY,
            file_id VARCHAR(100) NOT NULL,
        );
        """
        await self.execute(sql, execute=True)


    async def create_table_track_playlist(self):
        sql = """
        CREATE TABLE IF NOT EXISTS track_playlist (
        playlist_id INT REFERENCES user_playlists(playlist_id) ON DELETE CASCADE,
        track_id VARCHAR(100) NOT NULL,
        track_title VARCHAR(255) NOT NULL
        );
        """
        await self.execute(sql, execute=True)


    @staticmethod
    def format_args(sql, parameters: dict):
        sql += " AND ".join([
            f"{item} = ${num}" for num, item in enumerate(parameters.keys(),
                                                          start=1)
        ])
        return sql, tuple(parameters.values())

    async def select_video_by_id(self, video_id):
        sql = "SELECT * FROM videos WHERE video_id=$1;"
        return await self.execute(sql, video_id, fetchrow=True)

    async def select_all_users(self):
        sql = "SELECT * FROM users"
        return await self.execute(sql, fetch=True)

    async def select_user(self, **kwargs):
        sql = "SELECT * FROM users WHERE "
        sql, parameters = self.format_args(sql, parameters=kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def select_user_playlists(self, telegram_id, limit, offset):
        sql = """SELECT * FROM user_playlists 
        WHERE user_telegram_id=$1
        ORDER BY playlist_id ASC
        LIMIT $2 OFFSET $3;"""
        return await self.execute(sql, telegram_id, limit, offset, fetch=True)

    async def select_user_playlist(self, playlist_id):
        if type(playlist_id) is not int:
            playlist_id = int(playlist_id)
        sql = "SELECT * FROM user_playlists WHERE playlist_id=$1;"
        return await self.execute(sql, playlist_id, fetchrow=True)

    async def select_user_tracks_from_playlist(self, user_telegram_id, playlist_id):
        if type(playlist_id) is not int:
            playlist_id = int(playlist_id)
        sql = "SELECT * FROM user_playlists WHERE user_telegram_id=$1 AND playlist_id=$2;"
        result = await self.execute(sql, user_telegram_id, playlist_id, fetchrow=True)
        if not result:
            raise PlaylistNotFound
        sql = "SELECT * FROM track_playlist WHERE playlist_id=$1;"
        return await self.execute(sql, playlist_id, fetch=True)

    async def user_accepted_cond_terms(self, telegram_id):
        await self.execute("UPDATE users SET accepted_terms=True "
                           "WHERE telegram_id=$1;", telegram_id, execute=True)

    async def add_track_into_playlist(self, user_telegram_id, track_id, track_title, playlist_id):
        if type(playlist_id) is not int:
            playlist_id = int(playlist_id)
        sql = "SELECT * FROM user_playlists WHERE playlist_id=$1 AND user_telegram_id=$2;"
        result = await self.execute(sql, playlist_id, user_telegram_id, fetchrow=True)
        if not result:
            raise PlaylistNotFound
        sql = "SELECT COUNT(*) FROM track_playlist WHERE playlist_id=$1;"
        result = await self.execute(sql, playlist_id, fetchval=True)
        if result >= 100:
            raise LimitTracksInPlaylist
        sql = "INSERT INTO track_playlist (playlist_id, track_id, track_title) VALUES ($1, $2, $3)"
        await self.execute(sql, playlist_id, track_id, track_title, execute=True)

    async def count_users(self):
        sql = "SELECT COUNT(*) FROM users"
        return await self.execute(sql, fetchval=True)

    async def count_song_in_user_playlist(self, playlist_id):
        return await self.execute("SELECT COUNT(*) FROM track_playlist WHERE playlist_id=$1;", playlist_id,
                                  fetchval=True)

    async def count_of_user_playlists(self, telegram_id):
        sql = "SELECT COUNT(*) FROM user_playlists WHERE user_telegram_id=$1;"
        return await self.execute(sql, telegram_id, fetchval=True)

    async def edit_playlist_title(self, playlist_id, playlist_title, telegram_id):
        if type(playlist_id) is not int:
            playlist_id = int(playlist_id)
        sql = "UPDATE user_playlists SET playlist_title=$1 WHERE playlist_id=$2 AND user_telegram_id=$3;"
        await self.execute(sql, playlist_title, playlist_id, telegram_id, execute=True)

    async def add_new_playlist(self, user_telegram_id, playlist_title):
        sql = "INSERT INTO user_playlists (user_telegram_id, playlist_title) VALUES ($1, $2);"
        await self.execute(sql, user_telegram_id, playlist_title, execute=True)

    async def add_video(self, video_id, link, title):
        sql = """
        INSERT INTO videos (video_id, link, title) VALUES ($1, $2, $3);
        """
        try:
            await self.execute(sql, video_id, link, title, execute=True)
        except UniqueViolationError:
            pass

    async def add_audio(self, audio_id):
        sql = "INSERT INTO tracks (file_id) VALUES ($1);"
        await self.execute(sql, audio_id, execute=True)

    async def add_user(self, full_name, username, telegram_id, registration_date, accepted_terms):
        # CREATE TABLE IF NOT EXISTS users(
        # id SERIAL PRIMARY KEY,
        # full_name VARCHAR(128) NOT NULL,
        # username VARCHAR(36) NULL,
        # telegram_id BIGINT NOT NULL UNIQUE,
        # registration_date DATE NOT NULL,
        # accepted_terms BOOL NOT NULL
        sql = "INSERT INTO users (full_name, username, telegram_id, registration_date, accepted_terms) " \
              "VALUES($1, $2, $3, $4, $5) RETURNING *"
        return await self.execute(sql, full_name, username, telegram_id, registration_date, accepted_terms,
                                  fetchrow=True)

    async def update_data_in_db(self, data: dict):
        sql = "UPDATE users SET "
        sql += ", ".join(
            [f"{item} = ${num}" for num, item in enumerate(data.keys(),
                                                           start=1)])
        await self.execute(sql, *data.values(), execute=True)

    async def update_user_username(self, username, telegram_id):
        sql = "UPDATE users SET username=$1 WHERE telegram_id=$2"
        return await self.execute(sql, username, telegram_id, execute=True)

    async def delete_user_playlist(self, user_telegram_id, playlist_id):
        if type(playlist_id) is not int:
            playlist_id = int(playlist_id)
        result = await self.execute("DELETE FROM user_playlists WHERE playlist_id=$1 AND user_telegram_id=$2",
                                    playlist_id, user_telegram_id,
                                    execute=True)
        if int((result.split())[1]) != 1:
            raise PlaylistNotFound

    async def delete_song_from_user_playlist(self, user_telegram_id, playlist_id, song_number):
        result = await self.execute("SELECT * FROM user_playlists WHERE playlist_id=$1 AND user_telegram_id=$2",
                                    playlist_id, user_telegram_id, fetchrow=True)
        if not result:
            raise PlaylistNotFound
        # await self.execute("""
        # DELETE FROM track_playlist AS tp INNER JOIN (
        # SELECT track_id FROM track_playlist LIMIT 1 OFFSET $2) AS tp2
        # ON tp.track_id = tp2.track_id
        # WHERE tp.playlist_id=$1 AND tp.track_id = tp2.track_id;""",
        #                    playlist_id, song_number - 1, execute=True)
        await self.execute("""
        DELETE FROM track_playlist
        WHERE playlist_id = $1 AND track_id = (
            SELECT track_id
            FROM track_playlist
            OFFSET $2
            LIMIT 1);""",
                           playlist_id, song_number - 1, execute=True)



    async def delete_users(self):
        await self.execute("DELETE FROM users WHERE TRUE", execute=True)

    async def drop_users(self):
        await self.execute("DROP TABLE IF EXISTS users", execute=True)

    async def drop_questions(self):
        await self.execute("DROP TABLE IF EXISTS questions", execute=True)

    async def drop_user_playlists(self):
        await self.execute("DROP TABLE IF EXISTS user_playlists", execute=True)

    async def drop_videos(self):
        await self.execute("DROP TABLE IF EXISTS videos", execute=True)

    async def drop_track_playlist(self):
        await self.execute("DROP TABLE IF EXISTS track_playlist", execute=True)

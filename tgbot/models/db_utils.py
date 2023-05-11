from typing import Union


import asyncpg
from asyncpg import Pool, Connection, UniqueViolationError

from tgbot.config import load_config

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
        registration_date DATE NOT NULL
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
        playlist_id INT REFERENCES user_playlists(playlist_id) ON DELETE CASCADE
        track_id INT REFERENCES 
        );
        """


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
        LIMIT $2 OFFSET $3;"""
        return await self.execute(sql, telegram_id, limit, offset, fetch=True)

    async def count_users(self):
        sql = "SELECT COUNT(*) FROM users"
        return await self.execute(sql, fetchval=True)

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

    async def add_user(self, full_name, username, telegram_id, registration_date):
        sql = "INSERT INTO users (full_name, username, telegram_id, registration_date) " \
              "VALUES($1, $2, $3, $4)"
        await self.execute(sql, full_name, username, telegram_id, registration_date, fetchrow=True)

    async def update_data_in_db(self, data: dict):
        sql = "UPDATE users SET "
        sql += ", ".join(
            [f"{item} = ${num}" for num, item in enumerate(data.keys(),
                                                           start=1)])
        print(sql)
        await self.execute(sql, *data.values(), execute=True)

    async def update_user_username(self, username, telegram_id):
        sql = "UPDATE users SET username=$1 WHERE telegram_id=$2"
        return await self.execute(sql, username, telegram_id, execute=True)

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

from datetime import datetime
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
                      ) -> Union[asyncpg.Record, int, None, list]:
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

    async def create_table_thanks_to_devs(self):
        sql = """
        CREATE TABLE IF NOT EXISTS thanks_to_devs(
        telegram_id BIGINT UNIQUE REFERENCES users(telegram_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        is_approved BOOL NOT NULL
        );
        """

        await self.execute(sql, execute=True)

    async def create_table_users_subscriptions(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users_subscriptions (
        sub_id SERIAL PRIMARY KEY,
        telegram_id BIGINT REFERENCES users(telegram_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        sub_days INT NOT NULL,
        sub_status_id INT REFERENCES sub_statuses(sub_status_id) ON UPDATE RESTRICT ON DELETE RESTRICT
        );
        """
        await self.execute(sql, execute=True)

    async def create_table_active_subscriptions(self):
        sql = """
        CREATE TABLE IF NOT EXISTS active_subscriptions(
        sub_id INT REFERENCES users_subscriptions(sub_id) ON UPDATE CASCADE ON DELETE CASCADE,
        telegram_id BIGINT UNIQUE REFERENCES users(telegram_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        subscription_date_start DATE NOT NULL,
        subscription_date_end DATE NOT NULL
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

    async def create_table_sub_statuses(self):
        sql = """
        CREATE TABLE IF NOT EXISTS sub_statuses (
        sub_status_id INT PRIMARY KEY,
        status_name VARCHAR(20) NOT NULL
        );
        """
        await self.execute(sql, fetchrow=True)
        sql = """
        INSERT INTO sub_statuses (sub_status_id, status_name) VALUES
        (0, 'is_canceled'),
        (1, 'in_queue'),
        (2, 'is_active'),
        (3, 'is_finished')
        """
        try:
            await self.execute(sql, execute=True)
        except UniqueViolationError:
            pass

    async def create_table_premium_free_trials(self):
        sql = """
        CREATE TABLE IF NOT EXISTS premium_free_trials (
        telegram_id BIGINT UNIQUE REFERENCES users(telegram_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        free_trial_date_start DATE NOT NULL
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

    async def select_all_users_with_sub(self):
        sql = "SELECT * FROM users INNER JOIN active_subscriptions ON USING(telegram_id);"
        return await self.execute(sql, fetch=True)

    async def select_user(self, **kwargs):
        sql = "SELECT * FROM users WHERE "
        sql, parameters = self.format_args(sql, parameters=kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def check_user_terms(self, telegram_id):
        result: asyncpg.Record = await self.execute(
            "SELECT accepted_terms FROM users WHERE telegram_id=$1;", telegram_id,
            fetchrow=True)
        if not result:
            return False
        return result.get("accepted_terms")

    async def check_if_playlist_available(self, telegram_id, playlist_id, current_date):
        if isinstance(playlist_id, str):
            playlist_id = int(playlist_id)
        if (await self.check_subscription_is_valid(telegram_id, current_date)) is True:
            return True
        sql = """
        WITH available_playlists AS 
        (SELECT playlist_id FROM user_playlists 
        WHERE user_telegram_id=$1 
        ORDER BY playlist_id ASC 
        LIMIT 1)
        SELECT *
        FROM user_playlists INNER JOIN available_playlists USING(playlist_id)
        WHERE playlist_id=$2;
        """
        result = await self.execute(sql, telegram_id, playlist_id, fetch=True)
        return bool(result)

    async def add_user_to_thanks_to_devs_table(self, telegram_id):
        try:
            await self.execute("INSERT INTO thanks_to_devs (telegram_id, is_approved) VALUES ($1, False);",
                               telegram_id, execute=True)
        except UniqueViolationError:
            pass

    async def select_user_playlists(self, telegram_id, limit=0, offset=0):
        sql = """SELECT * FROM user_playlists 
        WHERE user_telegram_id=$1
        ORDER BY playlist_id ASC
        LIMIT $2 OFFSET $3;"""
        return await self.execute(sql, telegram_id, limit, offset, fetch=True)

    async def select_all_users_without_sub(self):
        sql = """
        SELECT telegram_id
        FROM users LEFT JOIN active_subscriptions USING(telegram_id) WHERE sub_id IS NULL;
        """
        return await self.execute(sql, fetch=True)

    async def select_all_users_without_active_sub_and_with_sub_in_queue(self):
        sql = """
        SELECT telegram_id
        FROM users 
        LEFT JOIN active_subscriptions USING(telegram_id)
        LEFT JOIN users_subscriptions USING(telegram_id)
        WHERE active_subscriptions.sub_id IS NULL AND users_subscriptions.sub_status_id = 1
        GROUP BY telegram_id;
        """
        return await self.execute(sql, fetch=True)

    async def gift_to_user_free_trial_premium(self, telegram_id, sub_days=14):
        """
        :param telegram_id:
        :param sub_days:
        :return:
        """
        sql = """
        INSERT INTO users_subscriptions (telegram_id, sub_days, sub_status_id) 
        SELECT $1, $2, 1
        WHERE NOT EXISTS (SELECT * FROM premium_free_trials WHERE telegram_id=$1) RETURNING *;
        """
        result = await self.execute(sql, telegram_id, sub_days, fetchrow=True)
        if result is not None:
            current_date = datetime.now()
            await self.add_user_into_free_trials_table(telegram_id, current_date)
            await self.activate_user_sub(telegram_id, current_date)
        return result

    async def add_user_into_free_trials_table(self, telegram_id, current_date):
        sql = """
        INSERT INTO premium_free_trials (telegram_id, free_trial_date_start) VALUES ($1, $2)
        """
        await self.execute(sql, telegram_id, current_date, execute=True)

    async def check_user_sub_then_unsub_if_not_valid(self, telegram_id, current_date):
        sql = """
        SELECT * FROM active_subscriptions WHERE telegram_id=$1 AND subscription_date_end < $2
        """
        result = await self.execute(sql, telegram_id, current_date,
                                    fetchrow=True)
        if result:
            await self.unsub_user_force(telegram_id, result["sub_id"])

    async def activate_user_sub(self, telegram_id, current_date):
        await self.check_user_sub_then_unsub_if_not_valid(telegram_id, current_date)
        sql = """
        INSERT INTO active_subscriptions (sub_id, telegram_id, subscription_date_start, subscription_date_end)
        SELECT sub_id, telegram_id, $2::date, $2::date + sub_days::integer
        FROM users_subscriptions 
        WHERE telegram_id=$1 AND sub_status_id=1 AND 
        NOT EXISTS (SELECT * FROM active_subscriptions WHERE telegram_id=$1) RETURNING *;
        """
        result = await self.execute(sql, telegram_id, current_date, fetchrow=True)
        if result:
            await self.execute("UPDATE users_subscriptions SET sub_status_id=2 WHERE sub_id=$1",
                               result["sub_id"], execute=True)

    async def group_all_valid_subscriptions_in_queue(self, telegram_id):
        sql = """
        SELECT SUM(sub_days) 
        FROM users_subscriptions
        WHERE telegram_id = $1 AND sub_status_id = 1
        GROUP BY telegram_id;
        """
        return await self.execute(sql, telegram_id, fetchval=True)

    async def unsub_user_force(self, sub_id, telegram_id):
        sql = """
        DELETE FROM active_subscriptions WHERE sub_id=$1 AND telegram_id=$2;
        """
        await self.execute(sql, sub_id, telegram_id, execute=True)
        sql = """
        UPDATE users_subscriptions SET sub_status_id=3 WHERE sub_id=$1 AND telegram_id=$2;
        """
        await self.execute(sql, sub_id, telegram_id, execute=True)

    async def activate_unsubs_with_subs_in_queue(self):
        """
        Если у пользователя имеется подписка в очереди, но нет активированной подписки, то эта функция найдёт
        подписку и активирует
        :param:
        :return:
        """
        all_unsubs = await self.select_all_users_without_active_sub_and_with_sub_in_queue()
        current_date = datetime.now()
        for user in all_unsubs:
            try:
                await self.activate_user_sub(user["telegram_id"], current_date)
            except:
                continue
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

    async def select_user_available_playlist(self, user_telegram_id):
        sql = "SELECT * FROM user_playlists WHERE user_telegram_id=$1 LIMIT 1;"
        return await self.execute(sql, user_telegram_id, fetchrow=True)

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

    async def initialize_new_user(self, user_telegram_id, full_name, username, registration_date, accepted_terms):
        user = await self.select_user(telegram_id=user_telegram_id)
        if not user:
            user = await self.add_user(full_name, username, user_telegram_id, registration_date, accepted_terms)
            count_of_user_playlists = await self.count_of_user_playlists(user_telegram_id)
            if count_of_user_playlists < 1:
                await self.add_new_playlist(user_telegram_id, "Избранное")
        return user

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

    async def select_valid_subscription_from_queue(self, telegram_id):
        sql = """
        SELECT * FROM users_subscriptions 
        WHERE telegram_id=$1 AND sub_status_id=1
        LIMIT 1;
        """
        return await self.execute(sql, telegram_id, fetchrow=True)

    # async def add_user_sub_from_queue_to_activate(self, telegram_id, current_date):
    #     subscription_in_queue = await self.select_valid_subscription_from_queue(telegram_id)
    #     if not subscription_in_queue:
    #         return
    #     sql = """
    #     UPDATE users_subscriptions SET sub_status_id = 2
    #     WHERE telegram_id=$1 AND sub_id=$2 AND sub_status_id=1;
    #     """
    #     await self.execute(sql, telegram_id, subscription_in_queue["sub_id"], execute=True)
    #     try:
    #         await self.execute("""
    #         INSERT INTO active_subscriptions (sub_id, telegram_id, subscription_date_start, subscription_date_end)
    #         VALUES ($1, $2, $3, $4);""", subscription_in_queue["sub_id"], telegram_id, current_date,
    #                            current_date + timedelta(subscription_in_queue["sub_days"]), execute=True)
    #     except UniqueViolationError:
    #         await self.execute("""
    #             UPDATE users_subscriptions SET sub_status_id = 1
    #             WHERE sub_id=$1;
    #         """)
    #     # await self.execute(sql, telegram_id, current_date, execute=True)

    async def add_subscription_to_queue(self, telegram_id, sub_days):
        sql = """
        INSERT INTO users_subscriptions (telegram_id, sub_days, sub_status_id) VALUES ($1, $2, 1);
        """
        await self.execute(sql, telegram_id, sub_days, execute=True)

    async def select_user_active_subscription(self, telegram_id, current_date):
        sql = """SELECT *
        FROM active_subscriptions
        WHERE telegram_id=$1 AND subscription_date_start <= $2 AND $2 <= subscription_date_end;"""
        return await self.execute(sql, telegram_id, current_date, fetchrow=True)

    async def add_user_subscription_to_queue_then_activate_if_need(self, telegram_id, current_date, sub_days):
        """
        sub_statuses: 0: cancelled,
                      1: in_queue,
                      2: is_active,
                      3: is_finished
        """
        await self.add_subscription_to_queue(telegram_id, sub_days)
        active_subscription = await self.select_user_active_subscription(telegram_id, current_date)
        if not active_subscription:
            await self.activate_user_sub(telegram_id, current_date)

    async def add_user(self, full_name, username, telegram_id, registration_date, accepted_terms):
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

    async def check_subscription_is_valid(self, telegram_id, current_date) -> bool:
        sql = """
        SELECT CASE WHEN subscription_date_start <= $1 AND $1 <= subscription_date_end THEN True 
        ELSE False END AS status
        FROM active_subscriptions
        WHERE telegram_id = $2;"""
        result = await self.execute(sql, current_date, telegram_id, fetchrow=True)
        if not result:
            return False
        return result.get("status")

    # TODO add check_subscriptions_is_non_valid

    async def delete_song_from_user_playlist(self, user_telegram_id, playlist_id, song_number):
        result = await self.execute("SELECT * FROM user_playlists WHERE playlist_id=$1 AND user_telegram_id=$2",
                                    playlist_id, user_telegram_id, fetchrow=True)
        if not result:
            raise PlaylistNotFound
        await self.execute("""
        DELETE FROM track_playlist
        WHERE playlist_id = $1 AND track_id = (
            SELECT track_id
            FROM track_playlist
            WHERE playlist_id = $1
            OFFSET $2
            LIMIT 1);""",
                           playlist_id, song_number - 1, execute=True)

    async def delete_users(self):
        await self.execute("DELETE FROM users WHERE TRUE", execute=True)

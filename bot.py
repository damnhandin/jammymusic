import asyncio
import logging
from datetime import datetime

import yandex_music.exceptions
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import ParseMode
from yandex_music import ClientAsync

from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.filters.check_terms_filter import CheckUserFilter
from tgbot.filters.group_filter import GroupFilter
from tgbot.filters.marketer_filter import MarketerFilter
from tgbot.handlers.add_own_song import register_add_own_music
from tgbot.handlers.admin import register_admin_handlers
from tgbot.handlers.chats_and_channels.search_song_in_chat import register_search_music_in_group
from tgbot.handlers.chats_and_channels.start_in_chat import register_default_commands_in_group
from tgbot.handlers.check_user_handlers import register_check_user_handlers
from tgbot.handlers.conditional_terms import register_conditional_terms_handlers
from tgbot.handlers.find_song_lyrics import register_find_lyrics
from tgbot.handlers.find_song_by_words import register_find_song_by_words
from tgbot.handlers.payment import register_payment
from tgbot.handlers.search_music import register_search_music
from tgbot.handlers.shazam import register_shazam
from tgbot.handlers.similar_songs_search import register_similar_songs_search
from tgbot.handlers.text_button_registration import text_button_registration
from tgbot.handlers.thanks_to_devs import register_thanks_to_devs_handlers
from tgbot.handlers.user import register_user
from tgbot.middlewares.active_users_middleware import ActiveUsers
from tgbot.middlewares.album import AlbumMiddleware
from tgbot.middlewares.environment import EnvironmentMiddleware
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.models.classes.paginator import PlaylistPaginator
from tgbot.models.db_utils import Database

logger = logging.getLogger(__name__)


async def init_db(db: Database):
    await db.create_table_users()
    await db.create_table_sub_statuses()
    await db.create_table_users_subscriptions()
    await db.create_table_active_subscriptions()
    await db.create_table_user_playlists()
    await db.create_table_videos()
    await db.create_table_track_playlist()
    await db.create_table_thanks_to_devs()
    await db.create_table_premium_free_trials()
    await db.create_table_transactions_history()
    await db.create_table_users_activity()

    # await db.init_sub_statuses()


async def setup_database(db: Database):
    logging.info("Создаём подключение к базе данных")
    await db.create()
    await init_db(db)
    logging.info("Готово")


async def delete_all_not_valid_subs(db):
    sql = """
    SELECT * FROM active_subscriptions WHERE subscription_date_end < $1;
    """
    current_date = datetime.now()
    non_valid_subs = await db.execute(sql, current_date, fetch=True)
    for user in non_valid_subs:
        await db.activate_user_sub(user["telegram_id"], current_date)


async def move_users_activity_to_db(db: Database):
    attendance_data = ActiveUsers.attendance_data
    await db.add_or_update_users_activity_db(attendance_data)


async def regular_functions(db: Database):
    await delete_all_not_valid_subs(db)
    await db.activate_unsubs_with_subs_in_queue()


async def long_timer_reg_funcs(db):
    await move_users_activity_to_db(db)


async def setup_regular_function(db: Database, start_timeout=45, timer_delay=25):
    await asyncio.sleep(start_timeout)
    while True:
        logging.info("Start regular functions")
        try:
            await regular_functions(db)
        except Exception as exc:
            logging.info(f"Error in regular function {exc}")
            await asyncio.sleep(timer_delay)
            continue
        await asyncio.sleep(timer_delay)


async def setup_long_regular_function(db: Database, start_timeout=45, long_timer_delay=1800):
    await asyncio.sleep(start_timeout)
    while True:
        logging.info("Start long regular functions")
        try:
            await long_timer_reg_funcs(db)
        except Exception as exc:
            logging.info(f"Error in long regular function {exc}")
            await asyncio.sleep(long_timer_delay)
            continue
        await asyncio.sleep(long_timer_delay)


def register_all_middlewares(playlist_paginator, dp, config, db, ya_music):
    dp.setup_middleware(EnvironmentMiddleware(playlist_pg=playlist_paginator, config=config, db=db,
                                              ya_music=ya_music))
    dp.setup_middleware(AlbumMiddleware())
    dp.setup_middleware(ThrottlingMiddleware())
    dp.setup_middleware(ActiveUsers())


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)
    dp.filters_factory.bind(MarketerFilter)
    dp.filters_factory.bind(CheckUserFilter)
    dp.filters_factory.bind(GroupFilter)


def register_all_handlers(dp, db):
    # admin handlers
    register_admin_handlers(dp)
    # Здесь хендлеры которые не сбрасывают состояние
    register_conditional_terms_handlers(dp)
    register_check_user_handlers(dp, db)
    # Самое главное чтобы в верхних хендлерах не сбрасывалось состояние
    register_default_commands_in_group(dp)
    register_search_music_in_group(dp)
    register_payment(dp)
    text_button_registration(dp)
    register_user(dp)
    register_similar_songs_search(dp)
    register_shazam(dp)
    register_find_lyrics(dp)
    register_find_song_by_words(dp)
    register_add_own_music(dp)
    register_search_music(dp)
    register_thanks_to_devs_handlers(dp)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")
    config = load_config(".env")
    storage = RedisStorage2() if config.tg_bot.use_redis else MemoryStorage()
    bot = Bot(token=config.tg_bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    db = Database()
    playlist_paginator = PlaylistPaginator(dp=dp)
    ya_music = await ClientAsync(config.tg_bot.ya_token).init()
    bot['config'] = config
    bot['db'] = db
    bot['playlist_pg'] = playlist_paginator
    register_all_middlewares(playlist_paginator, dp, config, db, ya_music)
    register_all_filters(dp)
    register_all_handlers(dp, db)
    await setup_database(db)
    asyncio.create_task(setup_regular_function(db))
    asyncio.create_task(setup_long_regular_function(db))
    # start
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")

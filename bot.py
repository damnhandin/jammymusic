import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admin import register_admin
from tgbot.handlers.echo import register_echo
from tgbot.handlers.user import register_user
from tgbot.middlewares.environment import EnvironmentMiddleware
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.models.classes.paginator import PlaylistPaginator
from tgbot.models.db_utils import Database

logger = logging.getLogger(__name__)


async def init_db(db: Database):
    # await db.drop_users()
    # await db.drop_track_playlist()
    # await db.drop_user_playlists()
    # await db.drop_videos()

    await db.create_table_users()
    await db.create_table_user_playlists()
    await db.create_table_videos()
    await db.create_table_track_playlist()


async def setup_database(db: Database):
    logging.info("Создаём подключение к базе данных")
    await db.create()
    await init_db(db)
    logging.info("Готово")


def register_all_middlewares(playlist_paginator, dp, config, db):
    dp.setup_middleware(EnvironmentMiddleware(playlist_pg=playlist_paginator, config=config, db=db))
    dp.setup_middleware(ThrottlingMiddleware())


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_admin(dp)
    register_user(dp)

    register_echo(dp)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")
    config = load_config(".env")

    storage = RedisStorage2() if config.tg_bot.use_redis else MemoryStorage()
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)
    db = Database()
    playlist_paginator = PlaylistPaginator()
    bot['config'] = config
    bot['db'] = db
    bot['playlist_pg'] = playlist_paginator

    register_all_middlewares(playlist_paginator, dp, config, db)
    register_all_filters(dp)
    register_all_handlers(dp)
    await setup_database(db)

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

from dataclasses import dataclass

from environs import Env


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str


@dataclass
class TgBot:
    token: str
    genius_token: str
    admin_ids: list[int]
    marketer_ids: list[int]
    use_redis: bool
    payment_token: str


@dataclass
class Miscellaneous:
    playlist_title_length_limit: int = 50
    other_params: str = None


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    misc: Miscellaneous


def load_config(path: str = None):
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            marketer_ids=list(map(int, env.list("MARKETERS"))),
            use_redis=env.bool("USE_REDIS"),
            genius_token=env.str("GENIUS_TOKEN"),
            payment_token=env.str("PAYMENT_TOKEN")
        ),
        db=DbConfig(
            host=env.str('DB_HOST'),
            password=env.str('DB_PASS'),
            user=env.str('DB_USER'),
            database=env.str('DB_NAME')
        ),
        misc=Miscellaneous(
            playlist_title_length_limit=50
        )
    )

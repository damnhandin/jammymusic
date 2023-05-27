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
    use_redis: bool


@dataclass
class Miscellaneous:
    playlist_title_length_limit: int = 50
    other_params: str = None

@dataclass
class Terms:
    cond_terms_text: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    misc: Miscellaneous
    terms: Terms

def load_config(path: str = None):
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            use_redis=env.bool("USE_REDIS"),
            genius_token=env.str("GENIUS_TOKEN")
        ),
        db=DbConfig(
            host=env.str('DB_HOST'),
            password=env.str('DB_PASS'),
            user=env.str('DB_USER'),
            database=env.str('DB_NAME')
        ),
        misc=Miscellaneous(
            playlist_title_length_limit=50
        ),
        terms=Terms(
            cond_terms_text="""Пользовательское соглашение

✌️Добро пожаловать! Этот бот предоставляет различные услуги в автоматизированном режиме. Прежде чем использовать данный бот, пожалуйста, ознакомьтесь с нашим пользовательским соглашением. Оно необходимо для законного функционирования нашего сервиса.

👌Пользователь бота несет ответственность за загрузку и распространение авторской музыки. Бот не несет ответственности за любые нарушения авторских прав, связанные с загрузкой и распространением музыки. Пользователь обязан использовать бота только в соответствии с действующим законодательством и нормами морали и этики.

❤️ Бот не гарантирует непрерывность и безошибочность своей работы. Мы будем стараться предоставлять нашим пользователям лучший сервис, однако не гарантируем, что бот будет работать без перебоев и ошибок.

⏸️ Бот может временно приостановить свою работу или изменить услуги, предоставляемые пользователям, без предварительного уведомления.

📝 Бот оставляет за собой право изменять пользовательское соглашение в любое время без предварительного уведомления пользователей. Пользователи обязуются периодически проверять это соглашение на наличие изменений. Пользовательское соглашение всегда будет доступно в закрепе официального канала проекта @jammy_music

Используя этот бот, пользователь соглашается со всеми условиями этого пользовательского соглашения.

❤️ Спасибо за использование нашего бота!"""
        )
    )

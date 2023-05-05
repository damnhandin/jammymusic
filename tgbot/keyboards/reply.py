from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=[
    [KeyboardButton("🎧 Мои плейлисты")],
    [KeyboardButton("🔍 Найти музыку"), KeyboardButton("🎵 Найти песню по словам")],
    [KeyboardButton("📄 Найти текст песни"), KeyboardButton("🎙 Shazam")],
    [KeyboardButton("🎼 Найти похожие треки"), KeyboardButton("😎 Добавить свой трек")]
])

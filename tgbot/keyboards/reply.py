from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=[
    [KeyboardButton("🎧 Мои плейлисты")],
    [KeyboardButton("🎙 Shazam"), KeyboardButton("🔍 Найти музыку")],
    [KeyboardButton("🎵 Найти песню по словам"), KeyboardButton("📄 Найти текст песни")],
    [KeyboardButton("😎 Добавить свой трек"), KeyboardButton("🎼 Найти похожие треки")]
])
# [KeyboardButton("Моя подписка")]

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup
import pylast
from tgbot.config import Config
from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import select_country_keyboard


async def charts_start_func(message: types.Message, state):
    await state.reset_state()
    await message.answer("Выбери страну, чтобы узнать популярные там песни", reply_markup=select_country_keyboard)


async def show_charts(mes: types.Message, callback_data, config: Config):
    await mes.answer("Ищу информацию по данному запросу!")
    network = pylast.LastFMNetwork(
        api_key=config.tg_bot.lastfm_api_key,
        api_secret=config.tg_bot.lastfm_api_secret,
        username=config.tg_bot.lastfm_username,
        password_hash=config.tg_bot.lastfm_password_hash,
    )
    music = network.get_geo_top_tracks(country=callback_data)
    chart = []

    for item in music:
        track = item.item
        artist = track.get_artist().get_name()
        title = track.get_title()
        chart.append(f'<b>{artist} - {title}</b>')
    chart_text = "\n".join(chart)
    await mes.answer(chart_text)


def register_chart_handlers(dp: Dispatcher):
    dp.register_message_handler(show_charts,  action_callback.filter(cur_action=["ru_chart", "es_chart", "us_chart"]))

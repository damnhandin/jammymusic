from aiogram import types, Dispatcher
from aiogram.types import ContentType

from tgbot.config import Config
import bot
from tgbot.misc.states import JammyMusicStates


async def donate(message: types.Message):
    await bot.Bot.send_invoice(message.chat.id, 'Премиум подписка',
                               ' Оформление премиум подписка в @Jammymusic', 'invoice',
                           Config.tg_bot.payment_token, 'RUB', [types.labeled_price('Премиум подписка', 30*100)])


async def get_unknown_content_to_donate(message: types.Message):
    await message.answer("Похоже, что вы хотели оплатить опдписку, но мы получили от вас нечто иное. "
                         "Прошипите /start чтобы вернуться в главное меню.")


async def success_donate(message: types.Message, state):
    await state.reset_state()
    await message.answer(f'Платеж прошел успешно {message.successful_payment.order_info}')


def register_payment(dp: Dispatcher):
    dp.register_message_handler(success_donate, content_types=ContentType.SUCCESSFUL_PAYMENT,
                                state=JammyMusicStates.donate)
    dp.register_message_handler(get_unknown_content_to_donate, content_types=ContentType.ANY,
                                state=JammyMusicStates.donate)
from aiogram import Dispatcher, types
from aiogram.types import ContentType

from tgbot.misc.states import JammyMusicStates


async def donate(message: types.Message, config):
    title_text = "Премиум подписка"
    desc_text = "Оформление премиум подписка в @Jammymusic"
    await message.bot.send_invoice(chat_id=message.chat.id,
                                   title=title_text,
                                   description=desc_text,
                                   payload='invoice',
                                   provider_token=config.tg_bot.payment_token,
                                   currency='RUB',
                                   prices=[types.LabeledPrice('Премиум подписка', 30*100)])


async def get_unknown_content_to_donate(message: types.Message):
    await message.answer("Похоже, что вы хотели оплатить подписку, но мы получили от вас нечто иное. "
                         "Прошипите /start чтобы вернуться в главное меню.")


async def success_donate(message: types.Message, state):
    await state.reset_state()
    await message.answer(f'Платеж прошел успешно {message.successful_payment.order_info}')


def register_payment(dp: Dispatcher):
    dp.register_message_handler(success_donate, content_types=ContentType.SUCCESSFUL_PAYMENT,
                                state=JammyMusicStates.donate)
    dp.register_message_handler(get_unknown_content_to_donate, content_types=ContentType.ANY,
                                state=JammyMusicStates.donate)

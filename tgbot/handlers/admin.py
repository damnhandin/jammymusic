from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import MediaGroupFilter
from aiogram.types import Message, ContentType

from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.callback_datas import action_callback
from tgbot.keyboards.inline import spam_sending_keyboard, update_sending_keyboard, spam_sending_approve_keyboard, \
    update_sending_approve_keyboard
from tgbot.misc.misc_funcs import convert_album_to_media_group, choose_content_and_func_for_sending
from tgbot.misc.states import JammyMusicStates
from tgbot.models.db_utils import Database


async def check_admin_status(message: Message):
    await message.reply("Hello, admin!")


async def get_my_id(message):
    await message.answer(f"<b>Ваш телеграм id:</b>\n{message.from_user.id}")


async def pre_handler_admin_start_sending_spam(message):
    await message.answer("Вы действительно хотите начать рассылку БЕСПЛАТНЫМ пользователям?",
                         reply_markup=spam_sending_keyboard)
    # await message.answer("Теперь отправьте сообщение, которое хотите отправить",
    #                      reply_markup=spam_sending_keyboard)


async def pre_handler_admin_start_sending_update(message: Message):
    await message.answer("Вы дейстительно хотите начать рассылку ВСЕМ пользователям?",
                        reply_markup=update_sending_keyboard)
    # await message.reply("Привет админ, начать рассылку пользователям об обновлении?",
    #                     reply_markup=update_sending_keyboard)


async def admin_start_sending_update(cq: types.CallbackQuery, state: FSMContext):
    await state.reset_state()
    await JammyMusicStates.update_sending.set()
    await cq.answer("Статус был успешно сброшен")
    await cq.message.answer("Теперь отправьте мне сообщение, которые хотите разослать пользователям, сообщение, "
                            "медафайл, либо несколько медиа сразу. Данное сообщение будет отправлено: "
                            "ВСЕМ пользователям")


async def admin_start_sending_spam(cq: types.CallbackQuery, state: FSMContext):
    await state.reset_state()
    await JammyMusicStates.spam_sending.set()
    await cq.answer("Статус был успешно сброшен")
    await cq.message.answer("Теперь отправьте мне сообщение, которые хотите разослать пользователям, сообщение, "
                            "медафайл, либо несколько медиа сразу. Данное сообщение будет отправлено: "
                            "БЕСПЛАТНЫМ пользователям")


async def admin_get_media_group_to_sending_update(message: types.Message, state: FSMContext, album: list[types.Message],
                                                  db: Database):
    await state.reset_data()
    media_group = types.MediaGroup()
    media_group = await convert_album_to_media_group(album, media_group)
    await state.update_data(sending_media_group=media_group)
    await message.answer_media_group(media=media_group)
    await message.answer("Вы действительно хотите разослать предыдущее сообщение ВСЕМ пользователям?",
                         reply_markup=update_sending_approve_keyboard)


async def admin_get_media_group_to_sending_spam(message: types.Message, state, album, db: Database):
    await state.reset_data()
    # users = await db.select_all_users_without_sub()
    media_group = types.MediaGroup()
    media_group = await convert_album_to_media_group(album, media_group)
    await state.update_data(sending_media_group=media_group)
    await message.answer_media_group(media=media_group)
    await message.answer("Вы действительно хотите разослать предыдущее сообщение БЕСПЛАТНЫМ пользователям?",
                         reply_markup=spam_sending_approve_keyboard)
    # await admin_sending_func(message.bot.send_media_group, users, media_group)


async def admin_get_msg_to_sending_update(message: types.Message, state: FSMContext, db: Database):
    await state.reset_data()
    # users = await db.select_all_users()
    await state.update_data(sending_message=message)
    await message.send_copy(chat_id=message.from_user.id)
    await message.answer("Вы действительно хотите разослать предыдущее сообщение ВСЕМ пользователям?",
                         reply_markup=update_sending_approve_keyboard)


async def admin_get_msg_to_sending_spam(message: types.Message, state, db):
    await state.reset_data()
    users = await db.select_all_users_without_sub()
    await state.update_data(sending_message=message)
    await message.send_copy(chat_id=message.from_user.id)
    # await admin_sending_func(message.send_copy, users)
    await message.answer("Вы действительно хотите разослать предыдущее сообщение БЕСПЛАТНЫМ пользователям?",
                         reply_markup=spam_sending_approve_keyboard)


async def update_approved(cq: types.CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await state.reset_state()
    users = await db.select_all_users()
    try:
        func = await choose_content_and_func_for_sending(data, users, cq.bot)
        if func is not None:
            await func
        else:
            await cq.message.answer("Произошла ошибка func is None")
            raise Exception("Произошла ошибка func is None")
    except Exception as exc:
        await cq.answer("Произошла ошибка")
        raise exc
    else:
        await cq.message.answer("Рассылка прошла успешно")


async def spam_approved(cq: types.CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await state.reset_state()
    users = await db.select_all_users_without_sub()
    try:
        func = choose_content_and_func_for_sending(data, users, cq.bot)
        if func is not None:
            await func
        else:
            await cq.message.answer("Произошла ошибка func is None")
            raise Exception("Произошла ошибка func is None")
    except Exception as exc:
        await cq.answer("Произошла ошибка")
        raise exc
    else:
        await cq.message.answer("Рассылка прошла успешно")


# async def send_update_default_message(message: types.Message, state: FSMContext, db: Database):
#     await state.reset_state(with_data=False)
#     update_text = "Дорогие пользователи @jammy_music_bot, \n " \
#                   "у нас произошло обновление, нажмите /start, \n" \
#                   "чтобы обновления успешно были произведены у вас"
#
#     users = await db.select_all_users()
#     await admin_sending_func(message.send_copy, users)


def register_admin_handlers(dp: Dispatcher):
    # All commands must be above other handlers
    # Все команды должны быть выше остальных хендлеров, что в случае ошибки, можно было использоваться другую команду
    dp.register_message_handler(get_my_id,
                                commands=["get_my_id"], state="*")
    dp.register_message_handler(check_admin_status,
                                AdminFilter(is_admin=True), commands=["admin_check"], state="*")
    dp.register_message_handler(pre_handler_admin_start_sending_update,
                                AdminFilter(is_admin=True), commands=["update"], state="*")
    dp.register_message_handler(pre_handler_admin_start_sending_spam,
                                AdminFilter(is_admin=True), commands=["spam"], state="*")
# dp.register_callback_query_handler(send_update_default_message,
#                                    AdminFilter(is_admin=True), commands=["update_sending"], state="*")
    # other handlers are below except handlers with commands
    # sending update func = sending for all users
    dp.register_callback_query_handler(admin_start_sending_spam,
                                       AdminFilter(is_admin=True), action_callback.filter(cur_action="spam_sending"),
                                       state="*")
    dp.register_callback_query_handler(admin_start_sending_update,
                                       AdminFilter(is_admin=True), action_callback.filter(cur_action="update_sending"),
                                       state="*")
    dp.register_message_handler(admin_get_media_group_to_sending_update,
                                AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=True),
                                state=JammyMusicStates.update_sending,
                                content_types=ContentType.ANY)
    dp.register_message_handler(admin_get_msg_to_sending_update,
                                AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=False),
                                state=JammyMusicStates.update_sending,
                                content_types=ContentType.ANY)
    # sending update func = sending only for free users, ex. sending ads messages
    dp.register_message_handler(admin_get_media_group_to_sending_spam,
                                AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=True),
                                state=JammyMusicStates.spam_sending,
                                content_types=ContentType.ANY)
    dp.register_message_handler(admin_get_msg_to_sending_spam,
                                AdminFilter(is_admin=True),
                                MediaGroupFilter(is_media_group=False),
                                state=JammyMusicStates.spam_sending,
                                content_types=ContentType.ANY)
    dp.register_callback_query_handler(update_approved, AdminFilter(is_admin=True),
                                       action_callback.filter("update_sending_approve"),
                                       state=JammyMusicStates.update_sending)
    dp.register_callback_query_handler(spam_approved, AdminFilter(is_admin=True),
                                       action_callback.filter("spam_sending_approve"),
                                       state=JammyMusicStates.spam_sending)


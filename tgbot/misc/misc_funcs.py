from aiogram import types


async def delete_all_messages_from_data(data: dict):
    for item in data.values():
        if isinstance(item, types.Message):
            try:
                await item.delete()
            except:
                continue
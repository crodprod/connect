import asyncio
import logging
import os
import platform
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.utils import markdown

from dotenv import load_dotenv
from bot_elements.database import DataBase
from bot_elements.lexicon import lexicon
from bot_elements.keyboards import kb_hello, kb_main, tasker_kb
from functions import load_config_file, update_config_file

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode="MarkdownV2")
dp = Dispatcher()

db = DataBase(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
)


async def is_pass_phrase_ok(table: str, pass_phrase: str):
    query = f"SELECT COUNT(*) as count FROM {table} WHERE pass_phrase = %s"
    db.connect()
    result = db.execute_query(query, (pass_phrase,))

    if result['count'] == 0:
        return False
    return True


async def is_registered(telegram_id: int):
    query = """
    SELECT telegram_id FROM children WHERE telegram_id = %s
    UNION
    SELECT telegram_id FROM mentors WHERE telegram_id = %s
    UNION
    SELECT telegram_id FROM teachers WHERE telegram_id = %s
    UNION 
    SELECT telegram_id FROM admins WHERE telegram_id = %s;

    """
    db.connect()
    result = db.execute_query(query, (telegram_id, telegram_id, telegram_id, telegram_id,))
    db.disconnect()
    # print("REGISTERED:", result)
    if result is None:
        return False
    return True


async def send_hello(telegram_id: int, table: str):
    query = f"SELECT * FROM {table} WHERE telegram_id = %s"
    db.connect()
    user_info = db.execute_query(query, (telegram_id,))
    if table == 'children':
        query = f"SELECT * FROM mentors WHERE group_num = %s"
        mentors_info = db.execute_query(query, (user_info['group_num'],), many=True)
        mentors = ""
        for mentor in mentors_info:
            mentors += f"{mentor['name']}\n"
        await bot.send_message(
            chat_id=telegram_id,
            text=lexicon['hello_messages']['children'].format(
                user_info['name'], user_info['group_num'],
                mentors
            ),
            reply_markup=kb_hello[table].as_markup()
        )
    elif table == 'mentors':
        query = "SELECT COUNT(*) as count FROM children WHERE group_num = %s"
        children_count = db.execute_query(query, (user_info['group_num'],))['count']
        other_mentors = ""
        query = "SELECT * FROM mentors WHERE group_num = %s"
        mentors_info = db.execute_query(query, (user_info['group_num'],), many=True)
        for mentor in mentors_info:
            if mentor['telegram_id'] != telegram_id:
                other_mentors += f"{mentor['name']}\n"
                # other_mentors += f"[Нажми](tg://resolve?user_id={mentor['telegram_id']})\n"
                # other_mentors += f"{mentor['name']}\n"
        await bot.send_message(
            chat_id=telegram_id,
            text=lexicon['hello_messages']['mentors'].format(
                user_info['name'], user_info['group_num'],
                children_count, other_mentors
            ),
            reply_markup=kb_hello[table].as_markup()
        )
    elif table == 'teachers':
        query = "SELECT * FROM modules WHERE id = %s"
        module_info = db.execute_query(query, (user_info['module_id'],))
        await bot.send_message(
            chat_id=telegram_id,
            text=lexicon['hello_messages']['teachers'].format(
                user_info['name'], module_info['name'],
                module_info['location']
            ),
            reply_markup=kb_hello[table].as_markup()
        )
    elif table == 'admins':
        await bot.send_message(
            chat_id=telegram_id,
            text=lexicon['hello_messages']['admins'].format(
                user_info['name'], markdown.markdown_decoration.spoiler(user_info['password'])
            ),
            reply_markup=kb_hello[table].as_markup()
        )
    db.disconnect()


@dp.message(CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r'(children|mentors|teachers|admins|tasker)_\w+'))))
async def deep_linking(message: Message, command: CommandObject):
    # print(command.args)
    target = command.args.split("_")[0]
    pass_phrase = command.args.split("_")[1]

    if target in ['children', 'mentors', 'teachers', 'admins']:
        if not await is_registered(message.chat.id):
            if await is_pass_phrase_ok(target, pass_phrase):
                query = f"UPDATE {target} SET telegram_id = %s WHERE pass_phrase = %s"
                db.connect()
                db.execute_query(query, (message.chat.id, pass_phrase,))
                db.disconnect()
                await send_hello(message.chat.id, target)
        else:
            await cmd_start(message)

    elif target == 'tasker':
        if platform.system() == "Windows":
            path = r"D:\CROD_MEDIA\tasker\taskapp_data\users.json"
        else:
            path = "/root/tasker/taskapp_data/users.json"
        tasker_users = load_config_file(path)
        fl = False
        for user in tasker_users:
            # print(user)
            if user['login'] == pass_phrase:
                fl = True
                user['tid'] = message.chat.id
                break
        if fl:
            update_config_file(tasker_users, path)
            await bot.send_message(
                chat_id=message.chat.id,
                text="*Твой телеграм\-аккаунт подключен\! Теперь новые задачи из Таскера будут приходить сюда*"
                     "\n\nСейчас ты можешь вернуться обратно",
                reply_markup=tasker_kb.as_markup()
            )



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    telegram_id = message.chat.id
    message_text = {
        'children': "*Ты в главном меню, выбери, что хочешь сделать*",
        'mentors': "*Выберите требуемое действие*",
        'teachers': "*Выберите требуемое действие*",
        'admins': "*Выберите требуемое действие*",
        None: "Чтобы начать пользоваться ботом, тебе нужно *отсканировать свой личный QR\-код\.* "
              "Если возникают трудности, обратись к воспитателям или администрации"

    }

    query = """
        SELECT 'children' AS status FROM children WHERE telegram_id = %s
        UNION ALL
        SELECT 'teachers' AS status FROM teachers WHERE telegram_id = %s
        UNION ALL
        SELECT 'mentors' AS status FROM mentors WHERE telegram_id = %s
        UNION ALL 
        SELECT 'admins' AS status FROM admins WHERE telegram_id = %s;
        """
    db.connect()
    user_status = db.execute_query(query, (telegram_id, telegram_id, telegram_id, telegram_id))
    db.disconnect()
    user_status = user_status['status'] if user_status else None

    if user_status is None:
        rm = None
    else:
        rm = kb_main[user_status].as_markup()

    await bot.send_message(
        chat_id=telegram_id,
        text=message_text[user_status],
        reply_markup=rm
    )


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

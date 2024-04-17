import asyncio
import datetime
import logging
import os
import platform
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.utils import markdown

from dotenv import load_dotenv

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory
from bot_elements.database import DataBase
from bot_elements.lexicon import lexicon
from bot_elements.keyboards import kb_hello, kb_main, tasker_kb, reboot_bot_kb, radio_kb
from functions import load_config_file, update_config_file
from wording.wording import get_grouplist

load_dotenv()
logging.basicConfig(level=logging.INFO)
current_directory = os.path.dirname(os.path.abspath(__file__))

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode="MarkdownV2")
dp = Dispatcher()

db = DataBase(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
)

months = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def screening_md_symbols(text: str):
    return text.replace(".", r"\.").replace("!", r"\!").replace("(", r"\(").replace(")", r"\)").replace("-", r"\-").replace("|", r"\|")


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


async def get_user_info(telegram_id: int, group: str):
    query = f"SELECT * FROM {group} WHERE telegram_id = %s"
    db.connect()
    result = db.execute_query(query, (telegram_id,))
    db.disconnect()
    # print("REGISTERED:", result)
    return result


async def get_user_status(telegram_id: int):
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
    return user_status


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


def update_env_var(variable, value):
    env_file_path = '.env'
    with open(env_file_path, 'r') as file:
        lines = file.readlines()

    for i in range(len(lines)):
        if lines[i].startswith(f'{variable}='):
            lines[i] = f'{variable}={value}\n'

    with open(env_file_path, 'w') as file:
        file.writelines(lines)


async def send_reboot_message(telegram_id: int):
    await bot.send_message(
        chat_id=telegram_id,
        text="*Перезагрузка бота*"
             "\n\nДля того, чтобы изменения вступили в силу, необходима перезагрузка бота\. Чтобы сделать это, нажмите на кнопку ниже",
        reply_markup=reboot_bot_kb.as_markup()
    )


async def get_module_children_list(module_id: int):
    query = "SELECT * FROM children WHERE id IN (SELECT child_id FROM modules_records WHERE module_id = %s)"
    db.connect()
    group_list = db.execute_query(query, (module_id,), many=True)
    db.disconnect()
    group_list.sort(key=lambda el: el['name'])

    return group_list


async def get_module_feedback_today(module_id: int):
    query = "SELECT mark, comment FROM feedback WHERE module_id = %s and date = %s"
    db.connect()
    feedback_list = db.execute_query(query, (module_id, datetime.datetime.now().date()), many=True)
    db.disconnect()
    return feedback_list


@dp.message(CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r'(children|mentors|teachers|admins|tasker)_\w+'))))
async def deep_linking(message: Message, command: CommandObject):
    # print(command.args)
    telegram_id = message.from_user.id
    target = command.args.split("_")[0]
    pass_phrase = command.args.split("_")[1]

    if target in ['children', 'mentors', 'teachers', 'admins']:
        if not await is_registered(telegram_id):
            if await is_pass_phrase_ok(target, pass_phrase):
                query = f"UPDATE {target} SET telegram_id = %s WHERE pass_phrase = %s"
                db.connect()
                db.execute_query(query, (telegram_id, pass_phrase,))
                db.disconnect()
                await send_hello(telegram_id, target)
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

    user_status = await get_user_status(telegram_id)

    if user_status is None:
        rm = None
    else:
        rm = kb_main[user_status].as_markup()

    await bot.send_message(
        chat_id=telegram_id,
        text=message_text[user_status],
        reply_markup=rm
    )


@dp.message(Command("setup"))
async def handle_setup_commands(message: types.Message):
    user_status = await get_user_status(message.from_user.id)
    if user_status == 'admins':
        command = message.text.split()
        if len(command) == 2:
            if command[1] in ['radio', 'errors', 'modules', 'fback']:
                # update_env_var(f'ID_GROUP_{command[1].upper()}', message.chat.id)
                await message.answer(
                    text="*Изменение беседы*"
                         f"\n\nДанная беседа установлена основной для *{command[1]}*"
                )
                await asyncio.sleep(1)
                await send_reboot_message(message.chat.id)
            else:
                await message.answer(
                    text=f"*Беседы {command[1]} не существует*\n\nДля изменения беседы введите"
                         f"\n/setup radio\|errors\|modules\|fback"
                )
        else:
            await message.answer(
                text="*Некорректная команда* \n\nДля изменения беседы введите"
                     "\n/setup radio\|errors\|modules\|fback"
            )
    else:
        print("ноунейм какой-то")


@dp.message(Command("radio"))
async def handle_radio_commands(message: types.Message):
    if message.chat.id == int(os.getenv('ID_GROUP_RADIO')):
        await message.answer(
            text="*Управление радио*"
                 "\n\nВыберите требуемое действие",
            reply_markup=radio_kb.as_markup()
        )


@dp.callback_query(F.data == "firststart")
async def send_random_value(callback: types.CallbackQuery):
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    await cmd_start(callback.message)


@dp.callback_query(MentorsCallbackFactory.filter())
async def callbacks_teachers(callback: types.CallbackQuery, callback_data: MentorsCallbackFactory):
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'mentors')
    print(user_info)
    if user_info['status'] == 'active':
        if action == "grouplist":
            await callback.message.delete()
            query = "SELECT * FROM children where group_num = %s"
            db.connect()
            group_list = db.execute_query(query, (user_info['group_num'],), many=True)
            db.disconnect()

            msg = await callback.message.answer(
                text="*Список группы создаётся\.\.\.*"
            )
            group_list_filename = get_grouplist(group_list, user_info['group_num'])
            filepath = f"{current_directory}/wording/generated/{group_list_filename}.pdf"

            await msg.delete()
            document = types.FSInputFile(filepath)
            await bot.send_document(
                chat_id=callback.from_user.id,
                document=document,
                caption=f"Список группы №{user_info['group_num']}",
                reply_markup=kb_hello['mentors'].as_markup()
            )
            if os.path.exists(filepath):
                os.remove(filepath)
        elif action == "feedback":
            query = "SELECT COUNT(*) AS count FROM feedback WHERE child_id IN (SELECT id from children WHERE group_num = %s) AND date = %s"
            db.connect()
            fb_count = db.execute_query(query, (user_info['group_num'], datetime.datetime.now().date(),))['count']
            query = "SELECT COUNT(*) AS count from children WHERE group_num = %s"
            group_count = db.execute_query(query, (user_info['group_num'],))['count']
            current_date = datetime.datetime.now().date().strftime('%d.%m.%Y')

            await callback.answer(
                text=f"Статистика за {current_date}"
                     f"\nОтправлено {fb_count} из {group_count} ",
                show_alert=True
            )
        elif action == "births":
            query = "SELECT c.* FROM children c JOIN shift_info s ON c.birth < s.end_date AND c.birth >= s.start_date AND c.group_num = %s"
            db.connect()
            birth_list = db.execute_query(query, (user_info['group_num'],), many=True)
            birth_list.sort(key=lambda el: el['birth'])
            if len(birth_list) > 0:
                await callback.message.delete()
                text = f"*Список именинников*\n\n"
                for child in birth_list:
                    text += f"{child['name']} \({child['birth'].day} {months[child['birth'].month]}\)"
                await callback.message.answer(
                    text=text,
                    reply_markup=kb_hello['mentors'].as_markup()
                )
            else:
                await callback.answer(
                    text="В вашей группе никто не будет праздновать день рождения",
                    show_alert=True
                )
    else:
        await callback.answer(
            text="⛔ Действие недоступно",
            show_alert=True
        )


@dp.callback_query(TeachersCallbackFactory.filter())
async def callbacks_teachers(callback: types.CallbackQuery, callback_data: TeachersCallbackFactory):
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'teachers')
    if user_info['status'] == 'active':
        query = "SELECT * FROM modules WHERE id = %s"
        db.connect()
        module_info = db.execute_query(query, (user_info['module_id'],))
        db.disconnect()

        if action == "grouplist":
            group_list = await get_module_children_list(user_info['module_id'])
            if len(group_list) > 0:
                await callback.message.delete()

                text = f"*Список группы по модулю «{module_info['name']}»*\n\n"

                for index, part in enumerate(group_list):
                    text += f"{index + 1}\. {part['name']} \({part['group_num']}\)\n"
                await callback.message.answer(
                    text=text,
                    reply_markup=kb_hello['teachers'].as_markup()
                )
            else:
                await callback.answer(
                    text="На ваш модуль пока никто не записался, попробуйте позже",
                    show_alert=True
                )
        elif action == "feedback":
            feedback_list = await get_module_feedback_today(user_info['module_id'])
            if len(feedback_list) > 0:
                await callback.message.delete()
                current_date = datetime.datetime.now().date().strftime('%d\.%m\.%Y')
                text = f"*Обратная связь по модулю «{module_info['name']}» за {current_date}*\n\n"
                for fb in feedback_list:
                    text += screening_md_symbols(f"Оценка: {fb['mark']}\nКомментарий: {fb['comment']}\n\n")
                await callback.message.answer(
                    text=text,
                    reply_markup=kb_hello['teachers'].as_markup()
                )

            else:
                await callback.answer(
                    text="Обратной связи за сегодняшний день ещё нет, попробуйте позже",
                    show_alert=True
                )
    else:
        await callback.answer(
            text="⛔ Действие недоступно",
            show_alert=True
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

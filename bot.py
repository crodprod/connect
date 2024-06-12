import asyncio
import datetime
import logging
import os
import platform
import re

import redis
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils import markdown, keyboard
from aiogram.methods import DeleteWebhook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dotenv import load_dotenv

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory, ChildrenCallbackFactory, RadioRequestCallbackFactory, SelectModuleCallbackFactory, AdminsCallbackFactory, \
    RecordModuleToChildCallbackFactory, FeedbackMarkCallbackFactory
from database import MySQL, RedisTable
from bot_elements.lexicon import lexicon, base_crod_url
from bot_elements.keyboards import kb_hello, kb_main, tasker_kb, reboot_bot_kb, radio_kb, check_apply_to_channel_kb
from bot_elements.signed_functions import create_signed_url
from bot_elements.states import Radio, Feedback
from bot_elements.functions import load_config_file, update_config_file
from wording.wording import get_grouplist, get_feedback

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)
SECRET_KEY = os.getenv('SECRET_KEY')

logging.basicConfig(level=logging.INFO)
current_directory = os.path.dirname(os.path.abspath(__file__))
config = load_config_file('config.json')

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode="html")
dp = Dispatcher()

db = MySQL(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    db_name=os.getenv('DB_NAME'),
    port=3310
)

redis = RedisTable(
    host=os.getenv('DB_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD')
)

redis.connect()

statuses = {
    'can_respond': True,
    'feedback': True,
    'modules_record': False,
    'radio': False
}
radio_request_user_list = []
feedback_temp_data_dict = {}

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


# to-do:
# Логика отправки обратки у детей
# Заявка на изменение модуля

def make_db_request(sql_query: str, params: tuple = ()):
    db.connect()
    db.execute(sql_query, params)
    db.disconnect()

    if db.result['status'] == "ok":
        return db.data
    return False


def get_text_link(title: str, link: str):
    return f"<a href='{link}'>{title}</a>"


def set_redis_hash(signature, index):
    redis.set(signature, index)


def dict_to_list(input_data):
    if type(input_data) == dict:
        return [input_data]
    return input_data


async def raise_error(error_text: str, tid=None):
    if tid is not None:
        await bot.send_message(
            chat_id=tid,
            text=f"Упс, случилась непредвиденная ошибка. Попробуй ещё раз или обратись к воспитателю или администратору"
                 f"\n\nОшибка: {error_text}"
        )


async def is_pass_phrase_ok(table: str, pass_phrase: str):
    query = f"SELECT COUNT(*) as count FROM {table} WHERE pass_phrase = %s"
    result = make_db_request(query, (pass_phrase,))

    if db.result['status'] == 'ok':
        if result['count'] == 0:
            return False
        return True
    else:
        await raise_error(db.result['message'])
        return None


async def get_user_info(telegram_id: int, group: str):
    query = f"SELECT * FROM {group} WHERE telegram_id = %s"
    result = make_db_request(query, (telegram_id,))
    if db.result['status'] == 'ok':
        return result
    else:
        await raise_error(db.result['message'], telegram_id)
        return None


async def get_user_status(column: str, value):
    query = f"""
            SELECT status FROM crodconnect.children WHERE {column} = {value}
            UNION ALL
            SELECT status FROM crodconnect.teachers WHERE {column} = {value}
            UNION ALL
            SELECT status FROM crodconnect.mentors WHERE {column} = {value}
            UNION ALL 
            SELECT status AS status FROM crodconnect.admins WHERE {column} = {value};
    """

    user_group = make_db_request(query)

    if db.result['status'] == 'ok':
        if not user_group:
            return 'alien'
        return user_group['status']
    else:
        await raise_error(db.result['message'], value)
        return None


async def get_user_group(telegram_id: int):
    query = """
            SELECT 'children' AS status FROM crodconnect.children WHERE telegram_id = %s
            UNION ALL
            SELECT 'teachers' AS status FROM crodconnect.teachers WHERE telegram_id = %s
            UNION ALL
            SELECT 'mentors' AS status FROM crodconnect.mentors WHERE telegram_id = %s
            UNION ALL 
            SELECT 'admins' AS status FROM crodconnect.admins WHERE telegram_id = %s;
            """

    user_group = make_db_request(query, (telegram_id, telegram_id, telegram_id, telegram_id))
    if db.result['status'] == 'ok':
        return user_group['status']
    else:
        await raise_error(db.result['message'], telegram_id)
        return None


async def get_module_list(callback: types.CallbackQuery):
    query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"

    modules = make_db_request(query)
    if db.result['status'] == 'ok':
        modules = dict_to_list(modules)
        if len(modules) > 0:
            await callback.message.delete()
            btns_builder = keyboard.InlineKeyboardBuilder()
            for module in modules:
                btns_builder.button(text=module['name'], callback_data=SelectModuleCallbackFactory(module_id=module['id'], name=module['name']))
            btns_builder.adjust(2)
            await callback.message.answer(
                text="<b>Выберите модуль для просмотра списка участников</b>",
                reply_markup=btns_builder.as_markup()
            )
        else:
            await callback.answer(
                text="Активные модули отсутствуют",
                show_alert=True
            )
    else:
        await raise_error(db.result['message'], callback.from_user.id)


async def send_hello(telegram_id: int, table: str):
    query = f"SELECT * FROM {table} WHERE telegram_id = %s and status = 'active'"

    user_info = make_db_request(query, (telegram_id,))
    if db.result['status'] == 'ok':
        if table == 'children':
            member_info = await bot.get_chat_member(chat_id=f"@{os.getenv('ID_CHANNEL')}", user_id=telegram_id)
            if type(member_info) != types.chat_member_left.ChatMemberLeft:
                query = f"SELECT * FROM crodconnect.mentors WHERE group_num = %s and status = 'active'"
                mentors_info = make_db_request(query, (user_info['group_num'],))
                if db.result['status'] == 'ok':
                    mentors_info = dict_to_list(mentors_info)
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
                else:
                    await raise_error(db.result['message'], telegram_id)
            else:
                await bot.send_message(
                    chat_id=telegram_id,
                    text="<b>Привет! Для начала тебе нужно подписаться на канал ЦРОДа, в нём мы публикуем все самые интересные новости о сменах и потоках</b>",
                    reply_markup=check_apply_to_channel_kb.as_markup()
                )
        elif table == 'mentors':
            query = "SELECT COUNT(*) as count FROM crodconnect.children WHERE group_num = %s"
            children_count = make_db_request(query, (user_info['group_num'],))['count']
            if db.result['status'] == 'ok':
                other_mentors = ""
                query = "SELECT * FROM crodconnect.mentors WHERE group_num = %s and status = 'active'"
                mentors_info = make_db_request(query, (user_info['group_num'],))
                if db.result['status'] == 'ok':
                    for mentor in mentors_info:
                        if mentor['telegram_id'] != telegram_id:
                            mntr = get_text_link(mentor['name'], f"tg://user?id={mentor['telegram_id']}")
                            other_mentors += f"{mntr}\n"
                    if not other_mentors:
                        other_mentors = "отсутствуют"
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=lexicon['hello_messages']['mentors'].format(
                            user_info['name'], user_info['group_num'],
                            children_count, other_mentors
                        ),
                        reply_markup=kb_hello[table].as_markup()
                    )
                else:
                    await raise_error(db.result['message'], telegram_id)
            else:
                await raise_error(db.result['message'], telegram_id)
        elif table == 'teachers':
            query = "SELECT * FROM crodconnect.modules WHERE id = %s"
            module_info = make_db_request(query, (user_info['module_id'],))
            if db.result['status'] == 'ok':
                await bot.send_message(
                    chat_id=telegram_id,
                    text=lexicon['hello_messages']['teachers'].format(
                        user_info['name'], module_info['name'],
                        module_info['location']
                    ),
                    reply_markup=kb_hello[table].as_markup()
                )
            else:
                await raise_error(db.result['message'], telegram_id)
        elif table == 'admins':
            await bot.send_message(
                chat_id=telegram_id,
                text=lexicon['hello_messages']['admins'].format(
                    user_info['name'], markdown.html_decoration.spoiler(user_info['password'])
                ),
                reply_markup=kb_hello[table].as_markup()
            )
    else:
        await raise_error(db.result['message'], telegram_id)


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
        text="<b>Перезагрузка бота</b>"
             "\n\nДля того, чтобы изменения вступили в силу, необходима перезагрузка бота. Чтобы сделать это, нажмите на кнопку ниже",
        reply_markup=reboot_bot_kb.as_markup()
    )


async def get_module_children_list(module_id: int):
    query = "SELECT * FROM crodconnect.children WHERE id IN (SELECT child_id FROM crodconnect.modules_records WHERE module_id = %s)"

    group_list = make_db_request(query, (module_id,))
    if db.result['status'] == 'ok':
        group_list = dict_to_list(group_list)

        group_list.sort(key=lambda el: el['name'])

        return group_list
    else:
        await raise_error(db.result['message'])
        return None


async def get_module_feedback_today(module_id: int):
    query = "SELECT mark, comment FROM crodconnect.feedback WHERE module_id = %s and date = %s"

    feedback_list = make_db_request(query, (module_id, datetime.datetime.now().date()))
    if db.result['status'] == 'ok':
        feedback_list = dict_to_list(feedback_list)
        return feedback_list
    else:
        await raise_error(db.result['message'])
        return None


@dp.message(CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r'(children|mentors|teachers|admins|tasker)_\w+'))))
async def deep_linking(message: Message, command: CommandObject):
    telegram_id = message.from_user.id
    target = command.args.split("_")[0]
    pass_phrase = command.args.split("_")[1]

    if target in ['children', 'mentors', 'teachers', 'admins']:
        user_status = await get_user_status('telegram_id', telegram_id)
        if user_status is not None:
            if user_status == 'alien':
                passed = await is_pass_phrase_ok(target, pass_phrase)
                if passed:
                    query = f"UPDATE {target} SET telegram_id = %s, status = 'active' WHERE pass_phrase = %s"

                    make_db_request(query, (telegram_id, pass_phrase,))
                    if db.result['status'] == 'ok':
                        await send_hello(telegram_id, target)
                    else:
                        await raise_error(db.result['message'], telegram_id)
            else:
                await cmd_start(message)

    elif target == 'tasker':
        if platform.system() == "Windows":
            path = r"D:\CROD_MEDIA\tasker\taskapp_data\users.json"
        else:
            path = "/root/crod/tasker/taskapp_data/users.json"
        tasker_users = load_config_file(path)
        fl = False
        for user in tasker_users:
            if user['login'] == pass_phrase:
                fl = True
                user['tid'] = message.chat.id
                user_status = user['status']
                break
        if fl:
            update_config_file(tasker_users, path)
            if user_status == "adm":
                message_text = "<b>Вы успешно создали доску в Таскере!</b>" \
                               f"\n\nКод для входа: {pass_phrase}" \
                               f"\nКод экрана: screen_{pass_phrase}" \
                               f"\n\nСейчас вы можете вернуться обратно в Таскер"
            else:
                message_text = "<b>Твой Telegram-аккаунт подключен! Теперь новые задачи из Таскера будут приходить сюда</b>" \
                               f"\n\nКод для входа: {pass_phrase}" \
                               "\n\nСейчас ты можешь вернуться обратно в Таскер"
            await bot.send_message(
                chat_id=message.chat.id,
                text=message_text,
                reply_markup=tasker_kb.as_markup()
            )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if statuses['can_respond']:
        telegram_id = message.chat.id
        message_text = {
            'children': "<b>Ты в главном меню, выбери, что хочешь сделать</b>",
            'mentors': "<b>Выберите требуемое действие</b>",
            'teachers': "<b>Выберите требуемое действие</b>",
            'admins': "<b>Выберите требуемое действие</b>",
            'frozen': "У вас временно <b>отсутствует доступ к боту.</b> Если вы считатете, что произошла ошибка, обратитесь к администрации",
            'alien': "Чтобы начать пользоваться ботом, тебе нужно <b>отсканировать свой личный QR-код.</b> "
                     "Если возникают трудности, обратись к воспитателям или администрации"

        }
        if str(telegram_id)[0] != '-':
            user_status = await get_user_status('telegram_id', telegram_id)
            if user_status is not None:
                user_group = user_status

                if user_status in ['alien', 'frozen']:
                    rm = None
                else:
                    user_group = await get_user_group(telegram_id)
                    if user_group is not None:
                        rm = kb_main[user_group].as_markup()
                    else:
                        return

                await bot.send_message(
                    chat_id=telegram_id,
                    text=message_text[user_group],
                    reply_markup=rm
                )
        else:
            if telegram_id == int(os.getenv('ID_GROUP_RADIO')):
                radio_builder = keyboard.InlineKeyboardBuilder()
                if not statuses['radio']:
                    text = "Чтобы включить радио, нажмите на кнопку ниже, дети получат сообщение и смогу отправлять заявки"
                    radio_builder.button(text="🟢 Включить радио", callback_data="radio_on")
                else:
                    text = "Чтобы выключить радио, нажмите на кнопку ниже, дети не смогут отправлять заявки"
                    radio_builder.button(text="🔴 Выключить радио", callback_data="radio_off")
                await message.answer(
                    text="<b>Управление радио</b>"
                         f"\n\n{text}",
                    reply_markup=radio_builder.as_markup()
                )


@dp.message(Command("radio"))
async def handle_radio_commands(message: types.Message):
    if message.chat.id == int(os.getenv('ID_GROUP_RADIO')):
        await message.answer(
            text="<b>Управление радио</b>"
                 "\n\nВыберите требуемое действие",
            reply_markup=radio_kb.as_markup()
        )


@dp.callback_query(F.data == "radio_on")
async def start_radio(callback: types.CallbackQuery):
    radio_request_user_list.clear()
    statuses['radio'] = True
    await callback.answer(
        text="🟢 Радио запущено, рассылаем информацию детям",
        show_alert=True
    )
    await callback.message.delete()
    query = "SELECT * FROM crodconnect.children where status = 'active'"

    children_list = make_db_request(query)
    if db.result['status'] == 'ok':
        for child in children_list:
            await bot.send_message(
                chat_id=child['telegram_id'],
                text="<b>Наше радио в эфире, ждём твою заявку!</b>"
                     "\n\nЧтобы отправить заявку, нажми /start"
            )
    else:
        await raise_error(db.result['message'], callback.from_user.id)


@dp.callback_query(F.data == "radio_off")
async def stop_radio(callback: types.CallbackQuery):
    radio_request_user_list.clear()
    statuses['radio'] = False
    await callback.answer(
        text="🔴 Радио остановлено, дети не могут отправлять заявки",
        show_alert=True
    )
    await callback.message.delete()


@dp.callback_query(F.data == "firststart")
async def send_random_value(callback: types.CallbackQuery):
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    await cmd_start(callback.message)


@dp.callback_query(MentorsCallbackFactory.filter())
async def callbacks_mentors(callback: types.CallbackQuery, callback_data: MentorsCallbackFactory):
    if statuses['can_respond']:
        action = callback_data.action
        user_status = await get_user_status('telegram_id', callback.from_user.id)
        if user_status is not None:
            if user_status == 'active':
                user_info = await get_user_info(callback.from_user.id, 'mentors')
                if user_info is not None:
                    if action == "grouplist":
                        await callback.message.delete()
                        query = "SELECT * FROM crodconnect.children where group_num = %s and status = 'active'"

                        group_list = make_db_request(query, (user_info['group_num'],))
                        if db.result['status'] == 'ok':
                            group_list = dict_to_list(group_list)
                            msg = await callback.message.answer(
                                text="<b>Список группы создаётся...</b>"
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
                        else:
                            await raise_error(db.result['message'], callback.from_user.id)

                    elif action == "feedback":
                        query = "SELECT COUNT(*) AS count FROM crodconnect.feedback WHERE child_id IN (SELECT id from crodconnect.children WHERE group_num = %s) AND date = %s"

                        fb_count = make_db_request(query, (user_info['group_num'], datetime.datetime.now().date(),))['count']
                        if db.result['status'] == 'ok':
                            query = "SELECT COUNT(*) AS count from crodconnect.children WHERE group_num = %s"
                            group_count = make_db_request(query, (user_info['group_num'],))['count']

                            current_date = datetime.datetime.now().date().strftime('%d.%m.%Y')

                            await callback.answer(
                                text=lexicon['callback_alerts']['mentor_fback_stat'].format(
                                    current_date, fb_count, group_count
                                ),
                                show_alert=True
                            )
                        else:
                            await raise_error(db.result['message'], callback.from_user.id)

                    elif action == "births":
                        query = "SELECT c.* FROM crodconnect.children c JOIN crodconnect.shift_info s ON c.birth < s.end_date AND c.birth >= s.start_date AND c.group_num = %s"

                        birth_list = make_db_request(query, (user_info['group_num'],))
                        if db.result['status'] == 'ok':
                            birth_list = dict_to_list(birth_list)
                            birth_list.sort(key=lambda el: el['birth'])
                            if len(birth_list) > 0:
                                await callback.message.delete()
                                text = f"<b>Список именинников</b>\n\n"
                                for child in birth_list:
                                    text += f"{child['name']} ({child['birth'].day} {months[child['birth'].month]})\n"
                                await callback.message.answer(
                                    text=text,
                                    reply_markup=kb_hello['mentors'].as_markup()
                                )
                            else:
                                await callback.answer(
                                    text=lexicon['callback_alerts']['no_births_group'],
                                    show_alert=True
                                )
                        else:
                            await raise_error(db.result['message'], callback.from_user.id)

                    elif action == "modules_list":
                        await get_module_list(callback)

                    elif action == "qrc":
                        await callback.message.delete()
                        target = 'children'
                        url = f"{base_crod_url}/connect/showqr/mentor?target={target}&value={user_info['group_num']}&initiator={callback.from_user.id}"

                        signature, signed_url = create_signed_url(url, SECRET_KEY)
                        set_redis_hash(signature, f"showqr_{callback.from_user.id}_{target}_{user_info['group_num']}")

                        btn = keyboard.InlineKeyboardBuilder().button(
                            text="QR-коды #️⃣",
                            web_app=types.WebAppInfo(
                                url=signed_url
                            )
                        )
                        await callback.message.answer(
                            text="Нажмите на кнопку, чтобы открыть список QR-кодов вашей группы",
                            reply_markup=btn.as_markup()
                        )
                    elif action == "traffic":
                        await callback.message.delete()
                        module_id = 1
                        url = f"{base_crod_url}/connect/modulecheck?mentor_id={user_info['id']}&module_id={module_id}&initiator={callback.from_user.id}"

                        signature, signed_url = create_signed_url(url, SECRET_KEY)
                        set_redis_hash(signature, f"modulecheck_{callback.from_user.id}_{user_info['id']}_{module_id}")

                        btn = keyboard.InlineKeyboardBuilder().button(
                            text="Посещаемость",
                            web_app=types.WebAppInfo(
                                url=signed_url
                            )
                        )
                        await callback.message.answer(
                            text="Нажмите на кнопку, чтобы отметить посещаемость",
                            reply_markup=btn.as_markup()
                        )

            else:
                await callback.answer(
                    text=lexicon['callback_alerts']['mentor_access_denied'],
                    show_alert=True
                )


@dp.callback_query(F.data == "check_apply")
async def check_apply_to_channel(callback: types.CallbackQuery):
    member_info = await bot.get_chat_member(chat_id=f"@{os.getenv('ID_CHANNEL')}", user_id=callback.message.chat.id)
    if type(member_info) != types.chat_member_left.ChatMemberLeft:
        await callback.message.delete()
        await send_hello(callback.message.chat.id, 'children')
    else:
        await callback.answer(
            text="Не нашли твою подписку, попробуй ещё раз и нажми на кнопку «✅ Я подписался(-ась)».",
            show_alert=True
        )


@dp.callback_query(F.data == "rebootbot")
async def check_apply_to_channel(callback: types.CallbackQuery):
    await callback.answer(
        text="(ЗАГЛУШКА) Бот перезагружается",
        show_alert=True
    )
    await callback.message.delete()


@dp.callback_query(SelectModuleCallbackFactory.filter())
async def callnacks_select_module(callback: types.CallbackQuery, callback_data: SelectModuleCallbackFactory):
    module_id, module_name = callback_data.module_id, callback_data.name
    group_list = await get_module_children_list(module_id)
    if group_list is not None:
        if len(group_list) > 0:
            await callback.message.delete()

            text = f"<b>Модуль «{module_name}»</b>\n\n"

            for index, part in enumerate(group_list):
                text += f"{index + 1}. {part['name']} ({part['group_num']})\n"
            await callback.message.answer(
                text=text,
                reply_markup=kb_hello['mentors'].as_markup()
            )
        else:
            await callback.answer(
                text=f"На модуль «{module_name}» ещё никто не записан",
                show_alert=True
            )


@dp.callback_query(TeachersCallbackFactory.filter())
async def callbacks_teachers(callback: types.CallbackQuery, callback_data: TeachersCallbackFactory):
    if statuses['can_respond']:
        action = callback_data.action
        user_status = await get_user_status('telegram_id', callback.from_user.id)
        if user_status is not None:
            if user_status == 'active':
                user_info = await get_user_info(callback.from_user.id, 'teachers')
                if user_info is not None:
                    query = "SELECT * FROM crodconnect.modules WHERE id = %s"

                    module_info = make_db_request(query, (user_info['module_id'],))
                    if db.result['status'] == 'ok':
                        if action == "grouplist":
                            group_list = await get_module_children_list(user_info['module_id'])
                            if group_list is not None:
                                if len(group_list) > 0:
                                    await callback.message.delete()

                                    text = f"<b>Модуль «{module_info['name']}»</b>\n\n"

                                    for index, part in enumerate(group_list):
                                        text += f"{index + 1}. {part['name']} ({part['group_num']})\n"
                                    await callback.message.answer(
                                        text=text,
                                        reply_markup=kb_hello['teachers'].as_markup()
                                    )
                                else:
                                    await callback.answer(
                                        text=lexicon['callback_alerts']['no_parts_in_module'],
                                        show_alert=True
                                    )
                        elif action == "feedback":
                            feedback_list = await get_module_feedback_today(user_info['module_id'])
                            if feedback_list is not None:
                                if len(feedback_list) > 0:
                                    await callback.message.delete()
                                    current_date = datetime.datetime.now().date().strftime('%d.%m.%Y')
                                    text = f"<b>Обратная связь по модулю «{module_info['name']}» за {current_date}</b>\n\n"
                                    for fb in feedback_list:
                                        text += f"Оценка: {fb['mark']}\nКомментарий: {fb['comment']}\n\n"
                                    await callback.message.answer(
                                        text=text,
                                        reply_markup=kb_hello['teachers'].as_markup()
                                    )

                                else:
                                    await callback.answer(
                                        text=lexicon['callback_alerts']['no_fback_teacher'],
                                        show_alert=True
                                    )
                    else:
                        await raise_error(db.result['message'], callback.from_user.id)
            else:
                await callback.answer(
                    text=lexicon['callback_alerts']['teacher_access_denied'],
                    show_alert=True
                )


@dp.message(Radio.request_text)
async def radio_text_sended(message: Message, state: FSMContext):
    await state.clear()
    if message.text == "/start":
        await cmd_start(message)
    else:
        builder_approve_radio = keyboard.InlineKeyboardBuilder()
        builder_approve_radio.button(text="🟢 Принять", callback_data=RadioRequestCallbackFactory(child_id=message.from_user.id, action="accept"))
        builder_approve_radio.button(text="🔴 Отклонить", callback_data=RadioRequestCallbackFactory(child_id=message.from_user.id, action="decline"))
        builder_approve_radio.adjust(1)
        await bot.send_message(
            chat_id=os.getenv('ID_GROUP_RADIO'),
            text="<b>Новая заявка</b>"
                 f"\n\n{message.text.strip()}",
            reply_markup=builder_approve_radio.as_markup()
        )
        await message.answer(
            text="<b>Твоя заявка отправлена и ждёт подтверждения</b>"
                 f"\n\n{message.text.strip()}",
            reply_markup=kb_hello['children'].as_markup()
        )
        radio_request_user_list.append(message.from_user.id)


@dp.message(Feedback.feedback_text)
async def feedback_mark_sended(message: Message, state: FSMContext):
    user_info = await get_user_info(message.from_user.id, "children")
    if user_info is not None:
        feedback = feedback_temp_data_dict[user_info['id']]
        await state.clear()
        if "/skip" in message.text:
            comment = "отсутствует"
        else:
            comment = message.text
        query = "INSERT INTO crodconnect.feedback (module_id, child_id, mark, comment, date) VALUES (%s, %s, %s, %s, %s)"

        make_db_request(query, (feedback['module_id'], user_info['id'], feedback['mark'], comment, datetime.datetime.now().date()))
        if db.result['status'] == 'ok':
            await bot.send_message(
                chat_id=os.getenv('ID_GROUP_FBACK'),
                text=f"<b>Модуль {feedback['module_name']}</b>"
                     f"\nОценка: {feedback['mark']}"
                     f"\nКомменатрий: {markdown.text(comment)}"
            )
            await create_feedback_proccess(user_info, feedback['callback'], "after")
        else:
            await raise_error(db.result['message'], message.from_user.id)


@dp.callback_query(RadioRequestCallbackFactory.filter())
async def callbacks_radio(callback: types.CallbackQuery, callback_data: RadioRequestCallbackFactory, state: FSMContext):
    child_id = callback_data.child_id
    action = callback_data.action
    radio_request_user_list.remove(child_id)
    await callback.message.delete_reply_markup()
    if action == 'accept':
        text = "📨<b>Тук-тук, новое сообщение</b>" \
               "\n\nТвоя заявка на радио обработана, жди в эфире уже совсем скоро!"
        status = callback.message.text + "\n\n🟢 Принято"
    elif action == 'decline':
        text = "📨<b>Тук-тук, новое сообщение</b>" \
               "\n\n<b>К сожалению, твоя заявка отклонена, возможно она не прошла цензуру, но ты можешь отправить новую, пока наше радио в эфире</b>"
        status = callback.message.text + "\n\n🔴 Отклонено"

    await callback.message.edit_text(callback.message.text + status)
    await bot.send_message(
        chat_id=child_id,
        text=text
    )


@dp.callback_query(AdminsCallbackFactory.filter())
async def callbacks_admins(callback: types.CallbackQuery, callback_data: AdminsCallbackFactory, state: FSMContext):
    if statuses['can_respond']:
        action = callback_data.action
        user_status = await get_user_status('telegram_id', callback.from_user.id)
        if user_status is not None:
            if user_status == 'active':
                print(action)
                if action == "modules_list":
                    await get_module_list(callback)

                elif action == "qr_list":
                    await callback.message.delete()
                    btn = keyboard.InlineKeyboardBuilder().button(
                        text="QR-коды #️⃣",
                        web_app=types.WebAppInfo(
                            url=f"{base_crod_url}/connect/showqr/admin?initiator={callback.from_user.id}"
                        )
                    )
                    await callback.message.answer(
                        text="Нажмите на кнопку, чтобы посмотреть QR-коды",
                        reply_markup=btn.as_markup()
                    )

            else:
                await callback.answer(
                    text=lexicon['callback_alerts']['access_denied'],
                    show_alert=True
                )


async def send_recorded_modules_info(child_id: int, callback: types.CallbackQuery):
    query = "SELECT * FROM crodconnect.modules WHERE id IN (SELECT module_id FROM crodconnect.modules_records WHERE child_id = %s)"
    recorded_modules_info = make_db_request(query, (child_id,))
    if db.result['status'] == 'ok':
        recorded_modules_info = dict_to_list(recorded_modules_info)
        text = "<b>Твои образовательные модули</b>\n\n"
        for index, module in enumerate(recorded_modules_info):
            query = "SELECT name FROM crodconnect.teachers WHERE module_id = %s"
            teacher_name = make_db_request(query, (module['id'],))['name']
            if db.result['status'] == 'ok':
                text += f"{index + 1}. {module['name']}" \
                        f"\n🧑‍🏫 {teacher_name}" \
                        f"\n📍 {module['location']}\n\n"
            else:
                await raise_error(db.result['message'], callback.from_user.id)
                return

        await callback.message.answer(
            text=text,
            reply_markup=kb_hello['children'].as_markup()
        )
    else:
        await raise_error(db.result['message'], callback.from_user.id)


@dp.callback_query(RecordModuleToChildCallbackFactory.filter())
async def callbacks_children(callback: types.CallbackQuery, callback_data: RecordModuleToChildCallbackFactory, state: FSMContext):
    query = "INSERT INTO crodconnect.modules_records (child_id, module_id) VALUES (%s, %s)"

    make_db_request(query, (callback_data.child_id, callback_data.module_id,))
    if db.result['status'] == 'ok':
        await recording_to_module_process(callback_data.child_id, callback)
    else:
        await raise_error(db.result['message'], callback.from_user.id)


async def generate_modules_list_to_record(child_id: int, callback: types.CallbackQuery):
    # выбрать модули, на которые чел не записан и на которых есть свободное место
    query = "SELECT * FROM crodconnect.modules WHERE id NOT IN (SELECT module_id FROM crodconnect.modules_records WHERE child_id = %s) AND seats_real < seats_max"

    modules_list = make_db_request(query, (child_id,))
    if db.result['status'] == 'ok':
        modules_list = dict_to_list(modules_list)
        query = "SELECT COUNT(*) AS count FROM crodconnect.modules_records WHERE child_id = %s"
        recorded_modules_count = make_db_request(query, (child_id,))['count']
        if db.result['status'] == 'ok':
            builder = keyboard.InlineKeyboardBuilder()

            for module in modules_list:
                builder.button(text=module['name'], callback_data=RecordModuleToChildCallbackFactory(child_id=child_id, module_id=module['id']))
            builder.adjust(1)
            await callback.message.answer(
                text=f"Выбери модуль №{recorded_modules_count + 1}",
                reply_markup=builder.as_markup()
            )
        else:
            await raise_error(db.result['message'], callback.from_user.id)

    else:
        await raise_error(db.result['message'], callback.from_user.id)


async def recording_to_module_process(child_id: int, callback: types.CallbackQuery):
    query = "SELECT * FROM crodconnect.modules_records WHERE child_id = %s"

    modules_records_list = make_db_request(query, (child_id,))
    if db.result['status'] == 'ok':
        modules_records_list = dict_to_list(modules_records_list)
        if len(modules_records_list) > 0:
            await callback.message.delete()
            if len(modules_records_list) == config['modules_count']:
                await send_recorded_modules_info(child_id, callback)
            else:
                await generate_modules_list_to_record(child_id, callback)
        else:
            if statuses['modules_record']:
                await callback.message.delete()
                await generate_modules_list_to_record(child_id, callback)
            else:
                await callback.answer(
                    text=lexicon['callback_alerts']['no_module_record'],
                    show_alert=True
                )
    else:
        await raise_error(db.result['message'], callback.from_user.id)


@dp.callback_query(FeedbackMarkCallbackFactory.filter())
async def callbacks_children(callback: types.CallbackQuery, callback_data: FeedbackMarkCallbackFactory, state: FSMContext):
    feedback_temp_data_dict[callback_data.child_id]['mark'] = callback_data.mark
    feedback_temp_data_dict[callback_data.child_id]['callback'] = callback
    await callback.message.delete()
    await callback.message.answer(
        f"<b>Обратная связь по модулю «{feedback_temp_data_dict[callback_data.child_id]['module_name']}»</b>"
        f"\nТвоя оценка: {callback_data.mark}"
        f"\n\nНапиши короткий комментарий к своей оценке (что понравилось, а что не очень)\nЕсли не хочешь ничего писать, то отправь /skip"
    )
    await state.set_state(Feedback.feedback_text)


async def create_feedback_proccess(user_info: [], callback: types.CallbackQuery, call_type: str = "new"):
    feedback_temp_data_dict[user_info['id']] = {}

    query = "SELECT * FROM crodconnect.modules WHERE id IN (SELECT module_id FROM crodconnect.modules_records WHERE child_id = %s) AND id NOT IN (SELECT module_id FROM crodconnect.feedback WHERE child_id = %s AND date = %s)"

    need_to_give_feedback_list = make_db_request(query, (user_info['id'], user_info['id'], datetime.datetime.now().date(),))
    if db.result['status'] == 'ok':
        if len(need_to_give_feedback_list) > 0:
            module = need_to_give_feedback_list[0]
            feedback_temp_data_dict[user_info['id']]['module_id'] = module['id']
            feedback_temp_data_dict[user_info['id']]['module_name'] = module['name']
            emojis = {1: "😠", 2: "☹", 3: "😐", 4: "🙂", 5: "😃", }
            builder = keyboard.InlineKeyboardBuilder()
            for i in range(1, 6):
                builder.button(text=f'{i}{emojis[i]}', callback_data=FeedbackMarkCallbackFactory(child_id=user_info['id'], module_id=module['id'], mark=i))
            builder.adjust(5)
            await bot.send_message(
                chat_id=user_info['telegram_id'],
                text=f"<b>Обратная связь по модулю «{module['name']}»</b>"
                     f"\n\nКак всё прошло? "
                     f"Выбери оценку от 1 до 5, где 1 - <b>очень плохо</b>, а 5 - <b>очень хорошо</b>",
                reply_markup=builder.as_markup()
            )
            return True
        else:
            if call_type == "after":
                await callback.message.answer(
                    text="Обратная связь за сегодня отправлена, спасибо!",
                    reply_markup=kb_hello['children'].as_markup()
                )
            return False
    else:
        await raise_error(db.result['message'], callback.from_user.id)
        return None


@dp.callback_query(ChildrenCallbackFactory.filter())
async def callbacks_children(callback: types.CallbackQuery, callback_data: ChildrenCallbackFactory, state: FSMContext):
    if statuses['can_respond']:
        action = callback_data.action
        user_status = await get_user_status('telegram_id', callback.from_user.id)
        if user_status is not None:
            if user_status == 'active':
                user_info = await get_user_info(callback.from_user.id, 'children')
                if user_info is not None:
                    if action == "modules":
                        await recording_to_module_process(user_info['id'], callback)

                    elif action == "feedback":
                        if statuses['feedback']:
                            passed = await create_feedback_proccess(user_info, callback)
                            if not passed:
                                await callback.answer(
                                    text="Ты уже отправил(-а) обратную связь по сегодняшим модулям, спасибо!",
                                    show_alert=True
                                )
                            elif passed:
                                await callback.answer()
                        else:
                            await callback.answer(
                                text=lexicon['callback_alerts']['no_fback_child'],
                                show_alert=True
                            )

                    elif action == "radio":
                        if statuses['radio']:
                            if user_info['telegram_id'] not in radio_request_user_list:
                                await callback.message.delete()
                                await state.set_state(Radio.request_text)
                                await callback.message.answer(
                                    text="<b>Радио ждёт именно тебя!</b>"
                                         "\n\nОтправь название песни, чтобы мы включили её на нашем радио " \
                                         "или напиши пожелание, которое мы озвучим в прямом эфире! (не забудь указать, кому адресовано пожелание)" \
                                         "\n\nЧтобы вернуться назад, отправь /start" \
                                         "\n\n_Все заявки проходят проверку на цензуру, поэтому не все песни могут прозвучать в эфире_"
                                )

                            else:
                                await callback.answer(
                                    text=lexicon['callback_alerts']['radio_request_already'],
                                    show_alert=True
                                )

                        else:
                            await callback.answer(
                                text=lexicon['callback_alerts']['no_radio'],
                                show_alert=True
                            )

            else:
                await callback.answer(
                    text=lexicon['callback_alerts']['child_access_denied'],
                    show_alert=True
                )


async def start_feedback():
    if statuses['can_respond']:
        statuses['feedback'] = True
        query = "SELECT * FROM crodconnect.children WHERE status = 'active'"

        children_list = make_db_request(query)
        if db.result['status'] == 'ok':
            for child in children_list:
                if child['telegram_id']:
                    await bot.send_message(
                        chat_id=child['telegram_id'],
                        text="Сбор обратной связи открыт!",
                        reply_markup=kb_hello['children'].as_markup()
                    )
        else:
            await raise_error(db.result['message'])


async def check_for_date():
    logging.info("Check for shift end")
    dates = load_config_file('config.json')['shift']['date']
    if not (datetime.datetime.strptime(dates['start'], '%Y-%m-%d') <= datetime.datetime.now() <= datetime.datetime.strptime(dates['end'], '%Y-%m-%d')):
        logging.info("Shift ended, responding to actions stopped")
        statuses['can_respond'] = False
        btn = keyboard.InlineKeyboardBuilder().button(
            text="Открыть Коннект",
            url=f"{base_crod_url}/connect"
        )
        text = "⛔ Бот отключен для детей, воспитателей и преподавателей. Чтобы открыть доступ к боту, добавьте дату начала и окончания следующей смены в Коннект"
        kb = btn.as_markup()

    else:
        logging.info("Shift not ended, running responding to actions")
        text = "✅ Бот доступен для всех групп пользователей"
        kb = None

    await bot.send_message(
        chat_id=os.getenv('ID_GROUP_ERRORS'),
        text="<b>Состояние бота</b>\n\n" + text,
        reply_markup=kb
    )


async def stop_feedback():
    if statuses['can_respond']:
        statuses['feedback'] = False
        query = "SELECT * FROM crodconnect.teachers WHERE status = 'active'"

        teachers_list = make_db_request(query)
        if db.result['status'] == 'ok':
            teachers_list = dict_to_list(teachers_list)
            for teacher in teachers_list:
                query = "SELECT * FROM crodconnect.feedback WHERE date = %s AND module_id = %s"
                feedback_list = make_db_request(query, (datetime.datetime.now().date(), teacher['module_id']))
                if db.result['status'] == 'ok':
                    if len(feedback_list) > 0:
                        query = "SELECT name FROM crodconnect.modules WHERE id = %s"
                        module_name = make_db_request(query, (teacher['module_id'],))['name']
                        if db.result['status'] == 'ok':
                            filename = get_feedback(module_name, feedback_list)
                            filepath = f"{current_directory}/wording/generated/{filename}.pdf"
                            document = types.FSInputFile(filepath)
                            date = datetime.datetime.now().date().strftime('%d.%m.%Y')
                            await bot.send_document(
                                chat_id=teacher['telegram_id'],
                                document=document,
                                caption=f"<b>Рассылка обратной связи</b>"
                                        f"\n\nОбратная связь по вашему модулю за {date}",
                                reply_markup=kb_hello['mentors'].as_markup()
                            )
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        else:
                            await raise_error(db.result['message'])
                            return
                    else:
                        await bot.send_message(
                            chat_id=teacher['telegram_id'],
                            text=f"<b>Рассылка обратной связи</b>"
                                 f"\n\n{' '.join(teacher['name'].split()[1:])}, за сегодняшний день по вашему образовательному модулю не было получено обратной связи",
                            reply_markup=kb_hello['teachers'].as_markup()
                        )
                else:
                    await raise_error(db.result['message'])
                    return
        else:
            await raise_error(db.result['message'])


async def main():
    await check_for_date()
    scheduler = AsyncIOScheduler()
    schedule = config['auto_actions']
    scheduler.add_job(
        start_feedback,
        "cron",
        day_of_week=schedule['start_feedback']['working_period'],
        hour=schedule['start_feedback']['hour'],
        minute=schedule['start_feedback']['minute']
    )
    scheduler.add_job(
        stop_feedback,
        "cron",
        day_of_week=schedule['stop_feedback']['working_period'],
        hour=schedule['stop_feedback']['hour'],
        minute=schedule['stop_feedback']['minute'])
    scheduler.add_job(
        check_for_date,
        "cron",
        day_of_week="mon-sun",
        hour=0,
        minute=0
    )
    scheduler.print_jobs()
    scheduler.start()
    if platform.system() != "Windows":
        await bot.send_message(
            chat_id=os.getenv('ID_GROUP_ERRORS'),
            text="<b>Перезагрузка сервисов</b>"
                 "\n\nТелеграмм-бот перезагружен!"
        )

    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

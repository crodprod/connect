import asyncio
import datetime
import logging
import os
import platform
import re
import time

import redis
import hmac
import hashlib
import base64

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils import markdown, keyboard
from aiogram.methods import DeleteWebhook
from aiogram.utils.markdown import link
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dotenv import load_dotenv

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory, ChildrenCallbackFactory, RadioRequestCallbackFactory, SelectModuleCallbackFactory, AdminsCallbackFactory, \
    RecordModuleToChildCallbackFactory, FeedbackMarkCallbackFactory
from bot_elements.database import DataBase
from bot_elements.lexicon import lexicon, base_crod_url
from bot_elements.keyboards import kb_hello, kb_main, tasker_kb, reboot_bot_kb, radio_kb, check_apply_to_channel_kb
from bot_elements.signed_functions import generate_signed_url
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

db = DataBase(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    port=3310
)

redis = redis.StrictRedis(
    host=os.getenv('DB_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD'),
    decode_responses=True
)

statuses = {
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

def get_text_link(title: str, link: str):
    return f"<a href='{link}'>{title}</a>"


def set_redis_hash(sign, index):
    redis.set(index, sign, 20)


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
    if result is None:
        return False
    return True


async def get_user_info(telegram_id: int, group: str):
    query = f"SELECT * FROM {group} WHERE telegram_id = %s"
    db.connect()
    result = db.execute_query(query, (telegram_id,))
    db.disconnect()
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


async def get_module_list(callback: types.CallbackQuery):
    query = "SELECT * FROM modules WHERE status = 'active'"
    db.connect()
    modules = db.execute_query(query, many=True)
    db.disconnect()
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


async def send_hello(telegram_id: int, table: str):
    query = f"SELECT * FROM {table} WHERE telegram_id = %s and status = 'active'"
    db.connect()
    user_info = db.execute_query(query, (telegram_id,))
    if table == 'children':
        print(f"@{os.getenv('ID_CHANNEL')}", telegram_id)
        member_info = await bot.get_chat_member(chat_id=f"@{os.getenv('ID_CHANNEL')}", user_id=telegram_id)
        if type(member_info) != types.chat_member_left.ChatMemberLeft:
            query = f"SELECT * FROM mentors WHERE group_num = %s and status = 'active'"
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
        else:
            await bot.send_message(
                chat_id=telegram_id,
                text="<b>Привет! Для начала тебе нужно подписаться на канал ЦРОДа, в нём мы публикуем все самые интересные новости о сменах и потоках</b>",
                reply_markup=check_apply_to_channel_kb.as_markup()
            )
    elif table == 'mentors':
        query = "SELECT COUNT(*) as count FROM children WHERE group_num = %s"
        children_count = db.execute_query(query, (user_info['group_num'],))['count']
        other_mentors = ""
        query = "SELECT * FROM mentors WHERE group_num = %s and status = 'active'"
        mentors_info = db.execute_query(query, (user_info['group_num'],), many=True)
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
        text="<b>Перезагрузка бота</b>"
             "\n\nДля того, чтобы изменения вступили в силу, необходима перезагрузка бота. Чтобы сделать это, нажмите на кнопку ниже",
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
    telegram_id = message.chat.id
    message_text = {
        'children': "<b>Ты в главном меню, выбери, что хочешь сделать</b>",
        'mentors': "<b>Выберите требуемое действие</b>",
        'teachers': "<b>Выберите требуемое действие</b>",
        'admins': "<b>Выберите требуемое действие</b>",
        None: "Чтобы начать пользоваться ботом, тебе нужно <b>отсканировать свой личный QR-код.</b> "
              "Если возникают трудности, обратись к воспитателям или администрации"

    }
    if str(telegram_id)[0] != '-':
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


@dp.message(Command("setup"))
async def handle_setup_commands(message: types.Message):
    user_status = await get_user_status(message.from_user.id)
    if user_status == 'admins':
        command = message.text.split()
        if len(command) == 2:
            if command[1] in ['radio', 'errors', 'modules', 'fback']:
                # update_env_var(f'ID_GROUP_{command[1].upper()}', message.chat.id)
                await message.answer(
                    text="<b>Изменение беседы</b>"
                         f"\n\nДанная беседа установлена основной для <b>{command[1]}</b>"
                )
                await asyncio.sleep(1)
                await send_reboot_message(message.chat.id)
            elif command[1] == "channel":
                await message.answer(
                    text="<b>Изменение ссылки на Telegram-канал</b>"
                         "\n\nОтправьте новый ник канала в формате _@название_канала_"
                         "\n\nЕсли передумали, отправьте /start"
                )
            #     to-do: логика обновления ссылки на канал
            else:
                await message.answer(
                    text="<b>Некорректная команда</b> \n\nДля изменения беседы отправьте"
                         "\n/setup radio|errors|modules|fback"
                         "\n\nДля изменения ссылки на Telegram-канал отправьте"
                         "\n/setup channel"
                )
        else:
            await message.answer(
                text="<b>Некорректная команда</b> \n\nДля изменения беседы отправьте"
                     "\n/setup radio|errors|modules|fback"
                     "\n\nДля изменения ссылки на Telegram-канал отправьте"
                     "\n/setup channel"
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
    query = "SELECT * FROM children where status = 'active'"
    db.connect()
    children_list = db.execute_query(query, many=True)
    db.disconnect()
    for child in children_list:
        await bot.send_message(
            chat_id=child['telegram_id'],
            text="<b>Наше радио в эфире, ждём твою заявку!</b>"
                 "\n\nЧтобы отправить заявку, нажми /start"
        )


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
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'mentors')
    if user_info is not None and user_info['status'] == 'active':
        if action == "grouplist":
            await callback.message.delete()
            query = "SELECT * FROM children where group_num = %s and status = 'active'"
            db.connect()
            group_list = db.execute_query(query, (user_info['group_num'],), many=True)
            db.disconnect()

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
        elif action == "feedback":
            query = "SELECT COUNT(*) AS count FROM feedback WHERE child_id IN (SELECT id from children WHERE group_num = %s) AND date = %s"
            db.connect()
            fb_count = db.execute_query(query, (user_info['group_num'], datetime.datetime.now().date(),))['count']
            query = "SELECT COUNT(*) AS count from children WHERE group_num = %s"
            group_count = db.execute_query(query, (user_info['group_num'],))['count']
            db.disconnect()
            current_date = datetime.datetime.now().date().strftime('%d.%m.%Y')

            await callback.answer(
                text=lexicon['callback_alerts']['mentor_fback_stat'].format(
                    current_date, fb_count, group_count
                ),
                show_alert=True
            )
        elif action == "births":
            query = "SELECT c.* FROM children c JOIN shift_info s ON c.birth < s.end_date AND c.birth >= s.start_date AND c.group_num = %s"
            db.connect()
            birth_list = db.execute_query(query, (user_info['group_num'],), many=True)
            db.disconnect()
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
        elif action == "modules_list":
            await get_module_list(callback)
        elif action == "qrc":
            await callback.message.delete()
            target = 'children'
            url = f"{base_crod_url}/connect/showqr?target={target}&value={user_info['group_num']}"
            generator = generate_signed_url(url, SECRET_KEY)
            signed_url, sign = generator[0], generator[1]
            set_redis_hash(sign, f"{target}{user_info['group_num']}")
            print(signed_url)
            btn = keyboard.InlineKeyboardBuilder().button(
                text="Показать QR-коды #️⃣",
                web_app=types.WebAppInfo(
                    url=signed_url
                )
            )
            await callback.message.answer(
                text="Чтобы просмотреть список QR-кодов группы, нажмите на кнопку ниже и выберите ребёнка",
                reply_markup=btn.as_markup()
            )
        elif action == "traffic":
            await callback.message.delete()
            module_id = 1
            url = f"{base_crod_url}/connect/modulecheck?mentor_id={user_info['id']}&module_id={module_id}"
            generator = generate_signed_url(url, SECRET_KEY)
            signed_url, sign = generator[0], generator[1]
            set_redis_hash(sign, f"{user_info['id']}{module_id}")
            btn = keyboard.InlineKeyboardBuilder().button(
                text="Отметить посещаемость",
                web_app=types.WebAppInfo(
                    url=signed_url
                )
            )
            await callback.message.answer(
                text="Чтобы просмотреть список QR-кодов группы, нажмите на кнопку ниже и выберите ребёнка",
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
            text="Кажется, что ты  ещё не подписался (-ась) на канал, попробуй ещё раз",
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
    if len(group_list) > 0:
        await callback.message.delete()

        text = f"<b>Список группы по модулю «{module_name}»</b>\n\n"

        for index, part in enumerate(group_list):
            text += f"{index + 1}. {part['name']} ({part['group_num']})\n"
        await callback.message.answer(
            text=text,
            reply_markup=kb_hello['mentors'].as_markup()
        )
    else:
        await callback.answer(
            text="На данный модуль пока никто не записался",
            show_alert=True
        )


@dp.callback_query(TeachersCallbackFactory.filter())
async def callbacks_teachers(callback: types.CallbackQuery, callback_data: TeachersCallbackFactory):
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'teachers')
    if user_info is not None and user_info['status'] == 'active':
        query = "SELECT * FROM modules WHERE id = %s"
        db.connect()
        module_info = db.execute_query(query, (user_info['module_id'],))
        db.disconnect()

        if action == "grouplist":
            group_list = await get_module_children_list(user_info['module_id'])
            if len(group_list) > 0:
                await callback.message.delete()

                text = f"<b>Список группы по модулю «{module_info['name']}»</b>\n\n"

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
    feedback = feedback_temp_data_dict[user_info['id']]
    await state.clear()
    if "/skip" in message.text:
        comment = "отсутствует"
    else:
        comment = message.text
    query = "INSERT INTO feedback (module_id, child_id, mark, comment, date) VALUES (%s, %s, %s, %s, %s)"
    db.connect()
    db.execute_query(query, (feedback['module_id'], user_info['id'], feedback['mark'], comment, datetime.datetime.now().date()))
    await bot.send_message(
        chat_id=os.getenv('ID_GROUP_FBACK'),
        text=f"<b>Модуль {feedback['module_name']}</b>"
             f"\nОценка: {feedback['mark']}"
             f"\nКомменатрий: {markdown.text(comment)}"
    )
    await create_feedback_proccess(user_info, feedback['callback'], "after")


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
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'admins')
    if user_info is not None and user_info['status'] == 'active':
        if action == "modules_list":
            await get_module_list(callback)


    else:
        await callback.answer(
            text=lexicon['callback_alerts']['access_denied'],
            show_alert=True
        )


async def send_recorded_modules_info(child_id: int, callback: types.CallbackQuery):
    query = "SELECT * FROM modules WHERE id IN (SELECT module_id FROM modules_records WHERE child_id = %s)"
    recorded_modules_info = db.execute_query(query, (child_id,), many=True)
    text = "<b>Твои образовательные модули</b>\n\n"
    for index, module in enumerate(recorded_modules_info):
        query = "SELECT name FROM teachers WHERE module_id = %s"
        teacher_name = db.execute_query(query, (module['id'],))['name']
        text += f"{index + 1}. {module['name']}" \
                f"\n🧑‍🏫 {teacher_name}" \
                f"\n📍 {module['location']}\n\n"

    await callback.message.answer(
        text=text,
        reply_markup=kb_hello['children'].as_markup()
    )


@dp.callback_query(RecordModuleToChildCallbackFactory.filter())
async def callbacks_children(callback: types.CallbackQuery, callback_data: RecordModuleToChildCallbackFactory, state: FSMContext):
    query = "INSERT INTO modules_records (child_id, module_id) VALUES (%s, %s)"
    db.connect()
    db.execute_query(query, (callback_data.child_id, callback_data.module_id,))
    db.disconnect()
    await recording_to_module_process(callback_data.child_id, callback)


async def generate_modules_list_to_record(child_id: int, callback: types.CallbackQuery):
    # выбрать модули, на которые чел не записан и на которых есть свободное место
    query = "SELECT * FROM modules WHERE id NOT IN (SELECT module_id FROM modules_records WHERE child_id = %s) AND seats_real < seats_max"
    db.connect()
    modules_list = db.execute_query(query, (child_id,), many=True)
    query = "SELECT COUNT(*) AS count FROM modules_records WHERE child_id = %s"
    recorded_modules_count = db.execute_query(query, (child_id,))['count']
    db.disconnect()
    if modules_list is not None:
        builder = keyboard.InlineKeyboardBuilder()

        for module in modules_list:
            builder.button(text=module['name'], callback_data=RecordModuleToChildCallbackFactory(child_id=child_id, module_id=module['id']))
        builder.adjust(1)
        await callback.message.answer(
            text=f"Выбери модуль №{recorded_modules_count + 1}",
            reply_markup=builder.as_markup()
        )


async def recording_to_module_process(child_id: int, callback: types.CallbackQuery):
    query = "SELECT * FROM modules_records WHERE child_id = %s"
    db.connect()
    modules_records_list = db.execute_query(query, (child_id,), many=True)
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

    query = "SELECT * FROM modules WHERE id IN (SELECT module_id FROM modules_records WHERE child_id = %s) AND id NOT IN (SELECT module_id FROM feedback WHERE child_id = %s AND date = %s)"
    db.connect()
    need_to_give_feedback_list = db.execute_query(query, (user_info['id'], user_info['id'], datetime.datetime.now().date(),), many=True)
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


@dp.callback_query(ChildrenCallbackFactory.filter())
async def callbacks_children(callback: types.CallbackQuery, callback_data: ChildrenCallbackFactory, state: FSMContext):
    action = callback_data.action
    user_info = await get_user_info(callback.from_user.id, 'children')
    if user_info is not None and user_info['status'] == 'active':
        if action == "modules":
            await recording_to_module_process(user_info['id'], callback)

        elif action == "feedback":
            if statuses['feedback']:
                if not await create_feedback_proccess(user_info, callback):
                    await callback.answer(
                        text="Ты уже отправил(-а) обратную связь по сегодняшим модулям, спасибо!",
                        show_alert=True
                    )
                else:
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
    statuses['feedback'] = True
    query = "SELECT * FROM children WHERE status = %s"
    db.connect()
    children_list = db.execute_query(query, ('active',), many=True)
    for child in children_list:
        if child['telegram_id']:
            await bot.send_message(
                chat_id=child['telegram_id'],
                text="Сбор обратной связи открыт!",
                reply_markup=kb_hello['children'].as_markup()
            )


async def stop_feedback():
    statuses['feedback'] = False
    query = "SELECT * FROM teachers WHERE status = 'active'"
    db.connect()
    teachers_list = db.execute_query(query, many=True)
    for teacher in teachers_list:
        query = "SELECT * FROM feedback WHERE date = %s AND module_id = %s"
        feedback_list = db.execute_query(query, (datetime.datetime.now().date(), teacher['module_id']), many=True)
        if len(feedback_list) > 0:
            query = "SELECT name FROM modules WHERE id = %s"
            module_name = db.execute_query(query, (teacher['module_id'],))['name']
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
            # print(os.listdir('wording/generated'))
            if os.path.exists(filepath):
                os.remove(filepath)
        else:
            await bot.send_message(
                chat_id=teacher['telegram_id'],
                text=f"<b>Рассылка обратной связи</b>"
                     f"\n\n{' '.join(teacher['name'].split()[1:])}, за сегодняшний день по вашему образовательному модулю не было получено обратной связи",
                reply_markup=kb_hello['teachers'].as_markup()
            )


async def main():
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

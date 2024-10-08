import datetime
import logging
import math
import os
import platform
import random
import re
import subprocess
import time
import zipfile
from itertools import islice
from xkcdpass import xkcd_password as xp

import flet as ft
import qrcode
import redis
import requests
import xlrd
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from pypdf import PdfMerger

from transliterate import translit

import wording.wording
from bot_elements.functions import load_config_file, update_config_file
from database import MySQL, RedisTable
from flet_elements.classes import NewModule, NewAdmin, NewMentor, NewChild, ConfirmationCodeField, ExtraUsers
from flet_elements.dialogs import InfoDialog, LoadingDialog, BottomSheet
from flet_elements.functions import remove_folder_content, get_hello, get_system_list
from flet_elements.screens import screens
from flet_elements.systemd import reboot_systemd, check_systemd, services_list, make_update
from flet_elements.telegram import send_telegam_message, send_telegram_document, delete_telegram_message
from flet_elements.functions import is_debug
from flet_elements.user_statuses import user_statuses
from backup import mysql_backup

os.environ['FLET_WEB_APP_PATH'] = '/connect'
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)

for path in ['assets/qrc', 'wording/generated', 'wording/qr']:
    if not os.path.exists(os.path.join(current_directory, path)):
        logging.info(f'Creating folder {path}')
        os.mkdir(os.path.join(current_directory, path))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

startup = {
    'mysql': {
        'status': True,
        'msg': ""
    },
    'redis': {
        'status': True,
        'msg': ""
    }
}

db = MySQL(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    db_name=os.getenv('DB_NAME')
)

redis = RedisTable(
    host=os.getenv('DB_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD')
)

os.environ['BOT_NAME'] = requests.get(url=f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/getMe").json()['result']['username']
logging.info(f"BOT_NAME: {os.getenv('BOT_NAME')}")


def url_sign_check(sign: str, index: str):
    logging.info(f"Redis: finding signature {index} for {sign}")
    try:
        response = 0
        if redis.exists(index):
            if redis.get(index) == sign:
                response = 1
            else:
                response = -1
        logging.info(f"Redis: signature finded")
        redis.delete(index)
        return response
    except Exception as e:
        logging.error(f"Redis: {e}")
        return -2


def convert_date(input_date):
    return datetime.datetime.strftime(datetime.datetime.strptime(input_date, '%Y-%m-%d'), '%d.%m.%Y')


def create_password():
    wordfile = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=wordfile, min_length=6, max_length=6)

    password = f"{xp.generate_xkcdpassword(mywords).split()[-1]}{random.randint(1111, 9999)}"

    return password


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER,
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.title = "Коннект"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        font_family="Geologica",
        # color_scheme=ft.ColorScheme(
        #     primary=ft.colors.WHITE
        # )
    )
    page.fonts = {
        "Geologica": "fonts/Geologica.ttf",
    }

    remaining_children_traffic = []
    child_col = ft.ListView()

    dlg_loading = LoadingDialog(page=page)
    dlg_info = InfoDialog(page=page)
    bottom_sheet = BottomSheet(page=page)

    redis.connect()
    db.connect()

    if db.result['status'] == "error":
        startup['mysql']['status'] = False
        startup['mysql']['msg'] = db.result['message']

    if redis.result['status'] == "error":
        startup['redis']['status'] = False
        startup['redis']['msg'] = redis.result['message']

    def make_db_request(sql_query: str, params: tuple = ()):
        db.execute(sql_query, params)

        if db.result['status'] == "ok":
            return db.data
        else:
            dlg_info.title = "Ошибка БД"
            dlg_info.content = ft.Text(
                f"При выполнении запроса к базе данных возникла ошибка, попробуйте позже или обратитесь к администратору."
                f"\n\nЗапрос: {sql_query}"
                f"\nОшибка: {db.result['message']}",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open()

    def is_telegrammed(target: str = None):
        messages = {
            None: "Не удалось отправить сообщение, так как вы не зарегистрированы в Telegram-боте. Попробуйте ещё раз после регистрации.",
            "confirm": "Не удалось отправить код подтверждения, так как вы не зарегистрированы в Telegram-боте. Попробуйте ещё раз после регистрации.",
            "docs": "Не удалось отправить документ, так как вы не зарегистрированы в Telegram-боте. Попробуйте выполнить запрос ещё раз после регистрации."
        }

        if password_field.data['telegram_id'] is None:
            dlg_info.title = "Отправка сообщения"
            dlg_info.content = ft.Text(messages[target], width=600, size=16, weight=ft.FontWeight.W_200)
            dlg_info.open()
            return False
        return True

    def change_child_group(e: ft.ControlEvent):
        child = e.control.data
        bottom_sheet.title = "Изменение группы"
        bottom_sheet.height = 120
        bottom_sheet.content = ft.Column(
            [
                ft.Text(f"{child['name']}\nВыберите новую группу", size=16, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER),
                ft.Row(
                    controls=[
                        ft.FilledTonalButton(text='1', on_click=lambda _: set_child_group(1)),
                        ft.FilledTonalButton(text='2', on_click=lambda _: set_child_group(2)),
                        ft.FilledTonalButton(text='3', on_click=lambda _: set_child_group(3)),
                        ft.FilledTonalButton(text='4', on_click=lambda _: set_child_group(4)),
                        ft.FilledTonalButton(text='5', on_click=lambda _: set_child_group(5))
                    ],
                    width=600,
                    scroll=ft.ScrollMode.AUTO
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        bottom_sheet.open()
        bottom_sheet.sheet.data = child

    def find_child(e: ft.ControlEvent):
        data = page.session.get('children_list')
        child_col.controls.clear()
        for child in data:
            if e.control.value.lower() in child['name'].lower():
                child_col.controls.append(
                    ft.ListTile(
                        title=ft.Text(child['name'], size=16),
                        subtitle=ft.Text(f"Группа №{child['group_num']}", size=14),
                        data=child,
                        on_click=change_child_group
                    )
                )
        page.update()

    def check_url(sign, index):
        response = url_sign_check(sign, index)
        text = {
            -2: "При получении данных возникла ошибка, попробуйте ещё раз.",
            -1: "Вы перешли по некорректной ссылке, попробуйте ещё раз.",
            0: "Ссылка, по которой вы перешли, недействительна, попробуйте ещё раз.",
            1: "Всё ок!"
        }

        if response in (0, -1, -2):
            change_screen("errors")
            dlg_info.title = "Ошибка доступа"
            dlg_info.content = ft.Text(text[response], width=600, size=16, weight=ft.FontWeight.W_200)
            dlg_info.open(action_btn_visible=False)
            return False
        return True

    def clean_all_children_info():
        """
        Удаляет все данные о детях из таблиц children, feedback, modules_records
        :return:
        """

        query = """
            TRUNCATE TABLE crodconnect.children;
            TRUNCATE TABLE crodconnect.feedback;
            TRUNCATE TABLE crodconnect.modules_records;
        """

        make_db_request(query)
        db.reconnect()

    def insert_children_info(table_filepath: str):
        dlg_loading.loading_text = "Добавляем детей"
        dlg_loading.open()
        wb = xlrd.open_workbook(table_filepath)
        ws = wb.sheet_by_index(0)
        rows_num = ws.nrows
        row = 1

        clean_all_children_info()

        while row < rows_num:
            dlg_loading.dialog.content.controls[0].controls[0].value = f"Добавляем детей {row}/{rows_num}"
            page.update()
            child = []
            for col in range(5):
                child.append(ws.cell_value(row, col))
            pass_phrase = create_passphrase(child[0])
            birth = xlrd.xldate.xldate_as_tuple(child[1], 0)
            birth = f"{birth[0]}-{birth[1]}-{birth[2]}"
            query = "INSERT INTO crodconnect.children (name, group_num, birth, comment, parrent_name, parrent_phone, pass_phrase) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            make_db_request(query, (child[0], random.randint(1, 5), birth, child[2], child[3], child[4], pass_phrase,))
            if db.result['status'] == 'error':
                dlg_loading.close()
                return
            row += 1
        dlg_loading.close()
        change_screen("main")
        open_sb("Список детей загружен", ft.colors.GREEN)
        if os.path.exists(f'assets/uploads/{table_filepath}'):
            os.remove(f'assets/uploads/{table_filepath}')

    def make_reboot(target: str):
        reboot_systemd(target)
        open_sb("Перезагружаем", ft.colors.GREEN)
        send_telegam_message(
            tID=os.getenv('ID_GROUP_ERRORS'),
            message_text=f"*Перезагрузка сервисов*"
                         f"\n\nЗапрос на перезагрузку сервиса {target}.service отправлен"
        )

        change_screen("reboot_menu")

    def get_reboot_card(title: str, icon, target: str):
        statuses = {
            True: {
                'icon': ft.Icon(ft.icons.CIRCLE, color=ft.colors.GREEN),
                'text': ft.Text("работает")
            },
            False: {
                'icon': ft.Icon(ft.icons.CIRCLE, color=ft.colors.RED),
                'text': ft.Text("не доступен")
            },
        }
        if is_debug():
            status_value = False
        else:
            status_value = check_systemd(target)
        card = ft.Card(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            ft.ListTile(
                                title=ft.Text(title),
                                # subtitle=ft.Row([statuses[status_value]['icon'], statuses[status_value]['text']], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                leading=statuses[status_value]['icon']
                            ),
                            expand=True
                        ),
                        ft.IconButton(
                            ft.icons.RESTART_ALT,
                            on_click=lambda _: make_reboot(target)
                        )
                    ]
                ),
                padding=ft.padding.only(right=10)
            ),
            width=600
        )

        return card

    def drawer_element_selected(e: ft.ControlEvent):
        data = e.control.data

        page.drawer.open = False
        page.update()
        time.sleep(0.3)

        if data['sec'] == "app":
            if data['act'] == "exit":
                password_field.value = ""
                change_screen("login")
            elif data['act'] == "home":
                change_screen("main")
            elif data['act'] == "qr_codes":
                change_screen("select_qr_group")

        elif data['sec'] == "children":
            if data['act'] == "update_table":
                open_confirmation("upload_children")
            elif data['act'] == "edit_group_num":
                change_screen("edit_child_group_num")
            elif data['act'] == "add_children":
                change_screen("add_child")
            elif data['act'] == "":
                pass

        elif data['sec'] == "modules":
            change_screen("modules_info")

        elif data['sec'] == "team":
            if data['act'] == "mentors":
                change_screen("mentors_info")
            elif data['act'] == "admins":
                change_screen("admins_info")

        elif data['sec'] == "documents":
            if data['act'] == "documents":
                change_screen("documents")

        elif data['sec'] == "settings":
            if data['act'] == "edit_stream":
                open_confirmation("edit_stream")
            elif data['act'] == "reboot":
                change_screen("reboot_menu")
            elif data['act'] == "about":
                change_screen("app_info")

    def create_passphrase(name):
        name = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', translit(''.join(name.split()[:2]), language_code='ru', reversed=True))
        phrase = f"{name}{os.urandom(3).hex()}"

        return phrase

    def add_new_child():
        query = "INSERT INTO crodconnect.children (name, group_num, birth, comment, parrent_name, parrent_phone, pass_phrase) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        pass_phrase = create_passphrase(new_child.name.value)

        month = '0' * (2 - len(new_child.birth_month.value)) + new_child.birth_month.value

        make_db_request(query, (new_child.name.value, new_child.group.value,
                                f"{new_child.birth_year.value}-{month}-{new_child.birth_day.value}",
                                new_child.caption.value, new_child.parent_name.value, f"+7{new_child.phone.value}", pass_phrase,))
        if db.result['status'] == 'ok':
            dlg_info.title = "Добавление ребёнка"
            dlg_info.content = ft.Text(
                f"{new_child.name.value} добавлен(-а) в группу №{new_child.group.value}. Информация отправлена воспитателям.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            change_screen('main')
            dlg_info.open()

    def add_new_mentor():
        query = "INSERT INTO crodconnect.mentors (name, group_num, pass_phrase) VALUES (%s, %s, %s)"
        name = new_mentor.name.value.strip()
        pass_phrase = create_passphrase(name)
        response = make_db_request(query, (name, new_mentor.group.value, pass_phrase))
        if response is not None:
            change_screen("mentors_info")
            open_sb("Воспитатель добавлен", ft.colors.GREEN)

    def add_new_module():
        dlg_loading.loading_text = "Добавляем модуль"
        dlg_loading.open()
        query = "INSERT INTO crodconnect.modules (name, seats_max, location) VALUES (%s, %s, %s)"
        make_db_request(query, (new_module.module_name.value, new_module.seats_count.value, new_module.locations_dropdown.value))

        query = "SELECT id FROM crodconnect.modules WHERE name = %s"
        module_id = make_db_request(query, (new_module.module_name.value,))['id']

        query = "INSERT INTO crodconnect.teachers (name, module_id, pass_phrase) VALUES (%s, %s, %s)"
        name = new_module.teacher_name.value.strip()
        pass_phrase = create_passphrase(name)

        response = make_db_request(query, (name, module_id, pass_phrase,))
        dlg_loading.close()
        if response is not None:
            change_screen("modules_info")
            open_sb("Модуль добавлен", ft.colors.GREEN)

    def add_new_admin():
        query = "INSERT INTO crodconnect.admins (name, pass_phrase, password, post, access) VALUES (%s, %s, %s, %s, %s)"
        name = new_admin.name.value.strip()
        post = new_admin.post.value.strip()
        access = 1 if new_admin.panel_access.value else 0
        pass_phrase = create_passphrase(name)
        password = create_password()
        response = make_db_request(query, (name, pass_phrase, password, post, access,))
        if response is not None:
            change_screen("admins_info")
            open_sb("Администратор добавлен", ft.colors.GREEN)

    def remove_mentor(e: ft.ControlEvent):
        query = "DELETE FROM crodconnect.mentors WHERE pass_phrase = %s"
        make_db_request(query, (e.control.data,))
        if db.result['status'] == "ok":
            open_sb("Воспитатель удалён")
            change_screen("mentors_info")

    def remove_admin(e: ft.ControlEvent):
        query = "DELETE FROM crodconnect.admins WHERE pass_phrase = %s"
        make_db_request(query, (e.control.data,))
        if db.result['status'] == "ok":
            open_sb("Администратор удалён")
            change_screen("admins_info")

    def remove_module(e: ft.ControlEvent):
        dlg_loading.loading_text = "Удаление модуля"
        dlg_loading.open()
        pass_phrase = page.session.get('remove_module_pass_phrase')
        page.session.remove('remove_module_pass_phrase')

        query = """
        DELETE FROM crodconnect.modules_records WHERE module_id = (SELECT module_id FROM crodconnect.teachers WHERE pass_phrase = %s);
        DELETE FROM crodconnect.modules WHERE id = (SELECT module_id FROM crodconnect.teachers WHERE pass_phrase = %s);
        DELETE FROM crodconnect.teachers WHERE pass_phrase = %s;
        """
        make_db_request(query, (pass_phrase, pass_phrase, pass_phrase,))
        dlg_loading.close()
        db.reconnect()
        if db.result['status'] == "ok":
            open_sb("Модуль удалён")
            change_screen("modules_info")

    def goto_remove_module(e: ft.ControlEvent):
        page.session.set('remove_module_pass_phrase', e.control.data)
        open_confirmation('remove_module')

    def goto_change_mentor_group(e: ft.ControlEvent):
        bottom_sheet.title = "Изменение группы"
        bottom_sheet.height = 100
        bottom_sheet.content = ft.Column(
            [
                ft.Text("Выберите новую группу", size=16, weight=ft.FontWeight.W_200),
                ft.Row(
                    controls=[
                        ft.FilledTonalButton(text='1', on_click=lambda _: change_mentor_group(1)),
                        ft.FilledTonalButton(text='2', on_click=lambda _: change_mentor_group(2)),
                        ft.FilledTonalButton(text='3', on_click=lambda _: change_mentor_group(3)),
                        ft.FilledTonalButton(text='4', on_click=lambda _: change_mentor_group(4)),
                        ft.FilledTonalButton(text='5', on_click=lambda _: change_mentor_group(5))
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    width=600
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        bottom_sheet.open()
        bottom_sheet.sheet.data = e.control.data

    def set_child_group(new_group: int):
        bottom_sheet.close()
        dlg_loading.loading_text = "Обновляем"
        dlg_loading.open()

        child = bottom_sheet.sheet.data

        query = "UPDATE crodconnect.children SET group_num = %s WHERE pass_phrase = %s"
        make_db_request(query, (new_group, child['pass_phrase'],))
        dlg_loading.close()
        if db.result['status'] == "ok":
            dlg_info.title = "Изменение группы"
            dlg_info.content = ft.Text(
                f"{child['name']} переведен(-а) в группу №{new_group}. Информация отправлена воспитателям.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open()

            query = "SELECT * FROM crodconnect.mentors WHERE group_num = %s AND status = 'active'"
            mentors = make_db_request(query, (new_group,))
            if type(mentors) == dict: mentors = [mentors]
            for mentor in mentors:
                send_telegam_message(
                    tID=mentor['telegram_id'],
                    message_text=f"{' '.join(mentor['name'].split()[1:])}, в вашу группу переведен(-а) *{child['name']}*"
                                 f"\n\n*Дата рождения:* {convert_date(str(child['birth']))}"
                                 f"\n*Особенности:* {child['comment']}"
                                 f"\n*Родитель:* {child['parrent_name']} ({child['parrent_phone']})"
                )

    def change_mentor_group(new_group: int):
        bottom_sheet.close()
        dlg_loading.loading_text = "Обновляем"
        dlg_loading.open()
        query = "UPDATE crodconnect.mentors SET group_num = %s WHERE pass_phrase = %s"
        make_db_request(query, (new_group, bottom_sheet.sheet.data,))
        dlg_loading.close()
        if db.result['status'] == "ok":
            change_screen('mentors_info')
            open_sb("Группа изменена", ft.colors.GREEN)

            query = "SELECT telegram_id from crodconnect.mentors WHERE pass_phrase = %s"
            mentor_tid = make_db_request(query, (bottom_sheet.sheet.data,))['telegram_id']
            if db.result['status'] == "ok":
                send_telegam_message(
                    tID=mentor_tid,
                    message_text="*Изменение группы*"
                                 f"\n\nВы были переведены администратором в *группу №{new_group}*"
                )

    def open_menu_drawer(e):
        page.drawer.open = True
        page.update()

    def generate_document(e: ft.ControlEvent):
        dlg_loading.loading_text = "Генерируем документ"
        dlg_loading.open()

        doctype = e.control.data['doctype']
        pdf_filepaths = []

        query = "SELECT telegram_id from crodconnect.admins WHERE password = %s"
        response = make_db_request(query, (password_field.value,))

        if is_telegrammed('docs'):
            caption = "*Генерация документов*\n\n"
            merger = PdfMerger()

            if doctype == "groups":

                for group_num in range(1, 6):
                    dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ (группа {group_num}/{5})"
                    page.update()

                    query = "SELECT * FROM crodconnect.children WHERE group_num = %s"
                    group_list = make_db_request(query, (group_num,))

                    if group_list is not None:
                        if group_list:
                            group_list.sort(key=lambda el: el['name'])

                            group_list_filename = wording.wording.get_grouplist(group_list, group_num)
                            filepath = f"{current_directory}/wording/generated/{group_list_filename}.pdf"

                            merger.append(filepath)
                            pdf_filepaths.append(group_list_filename)

                merged_filepath = f"{current_directory}/wording/generated/grouplist.pdf"
                merger.write(merged_filepath)
                merger.close()

                caption += "Списки групп с информацией о детях"
                if send_telegram_document(
                        tID=response['telegram_id'],
                        filepath=merged_filepath,
                        description=caption + "\n\n#документы"
                ):
                    open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                    remove_folder_content(f"{current_directory}/wording/generated")
                else:
                    open_sb("Ошибка Telegram", ft.colors.RED)

                if os.path.exists(merged_filepath):
                    os.remove(merged_filepath)
                for pdf in pdf_filepaths:
                    if os.path.exists(pdf):
                        os.remove(pdf)

            elif doctype == "qr":

                # для групп детей
                for group_num in range(1, 6):
                    dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ (группа {group_num}/{5})"
                    page.update()

                    query = "SELECT * FROM crodconnect.children WHERE group_num = %s AND status = 'waiting_for_registration'"
                    group_list = make_db_request(query, (group_num,))

                    if group_list is not None:
                        if group_list:
                            group_list.sort(key=lambda el: el['name'])

                            qr_list_groups_filename = wording.wording.get_qr_list("children", group_list, str(group_num))
                            filepath = f"{current_directory}/wording/generated/{qr_list_groups_filename}.pdf"

                            merger.append(filepath)
                            pdf_filepaths.append(qr_list_groups_filename)

                for s in ['mentors', 'teachers']:
                    dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ ({s})"
                    page.update()

                    query = f"SELECT * FROM {s} WHERE status = 'waiting_for_registration'"
                    group_list = make_db_request(query)

                    if group_list is not None:
                        if type(group_list) == dict: group_list = [group_list]
                        if group_list:
                            qr_list_groups_filename = wording.wording.get_qr_list(s, group_list)
                            filepath = f"{current_directory}/wording/generated/{qr_list_groups_filename}.pdf"
                            merger.append(filepath)
                            pdf_filepaths.append(qr_list_groups_filename)

                merged_filepath = f"{current_directory}/wording/generated/qrlist.pdf"
                merger.write(merged_filepath)
                merger.close()

                caption += "Таблица QR-кодов для регистрации в Telegram-бота"
                if send_telegram_document(
                        tID=response['telegram_id'],
                        filepath=merged_filepath,
                        description=caption + "\n\n#документы"
                ):
                    open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                else:
                    open_sb("Ошибка отправки в Telegram", ft.colors.RED)

                remove_folder_content(f"{current_directory}/wording/qr")
                remove_folder_content(f"{current_directory}/wording/generated")

                if os.path.exists(merged_filepath):
                    os.remove(merged_filepath)
                for pdf in pdf_filepaths:
                    if os.path.exists(pdf):
                        os.remove(pdf)

            elif doctype == "modules":
                query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
                modules_list = make_db_request(query)

                if db.result['status'] == 'ok':
                    if type(modules_list) == dict: modules_list = [modules_list]
                    if modules_list:
                        merger = PdfMerger()

                        for module in modules_list:
                            dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ ({module['name'][:10]}...)"
                            page.update()

                            query = "SELECT * FROM crodconnect.teachers WHERE module_id = %s"
                            teacher_info = make_db_request(query, (module['id'],))

                            if db.result['status'] == "ok":
                                query = "SELECT * FROM crodconnect.children WHERE id in (SELECT child_id FROM crodconnect.modules_records WHERE module_id = %s)"
                                children_list = make_db_request(query, (module['id'],))

                                if db.result['status'] == "ok":
                                    if type(children_list) == dict: children_list = [children_list]
                                    if children_list:
                                        children_list.sort(key=lambda el: el['name'])

                                        filename = wording.wording.get_module_parts(children_list, module, teacher_info)
                                        filepath = f"{current_directory}/wording/generated/{filename}.pdf"

                                        merger.append(filepath)
                                        pdf_filepaths.append(filename)

                        if len(pdf_filepaths) > 0:
                            merged_filepath = f"{current_directory}/wording/generated/modulelist.pdf"
                            merger.write(merged_filepath)
                            merger.close()

                            caption += "Состав образовательных модулей"

                            if send_telegram_document(
                                    tID=response['telegram_id'],
                                    filepath=merged_filepath,
                                    description=caption + "\n\n#документы"
                            ):
                                open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                            else:
                                open_sb("Ошибка отправки в Telegram", ft.colors.RED)

                            remove_folder_content(f"{current_directory}/wording/generated")
                            if os.path.exists(merged_filepath):
                                os.remove(merged_filepath)
                        else:
                            open_sb("Записи на модули отсутствуют")
                        for pdf in pdf_filepaths:
                            if os.path.exists(pdf):
                                os.remove(pdf)
            elif doctype == "navigation":
                shift = load_config_file('config.json')['shift']
                shift_name = shift['shift_list'][shift['current_shift']]['name']

                query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
                modules = make_db_request(query)

                if db.result['status'] == "ok":
                    if type(modules) == dict: modules = [modules]
                    navigation_filename = wording.wording.get_modules_navigation(modules, shift_name)
                    filepath = f"{current_directory}/wording/generated/{navigation_filename}.pdf"

                    caption += "Навигация по образовательным модулям"

                    if send_telegram_document(
                            tID=response['telegram_id'],
                            filepath=filepath,
                            description=caption + "\n\n#документы"
                    ):
                        open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                    else:
                        open_sb("Ошибка Telegram", ft.colors.RED)
                    if os.path.exists(filepath):
                        os.remove(filepath)

            elif doctype == 'badge':
                query = """
                    SELECT name, 'mentors' AS post_, group_num AS caption FROM crodconnect.mentors
                    UNION
                    SELECT name, 'teachers' AS post_, 'Наставник' AS caption FROM crodconnect.teachers
                    UNION
                    SELECT name, 'admins' AS post_, post AS caption FROM crodconnect.admins WHERE status != 'creator';
                """
                users = make_db_request(query)
                if db.result['status'] == 'ok':
                    for user in users:
                        if user['post_'] == 'mentors':
                            user['caption'] = f"Воспитатель {user['caption']} группы"

                        if not user['caption']: user['caption'] = ''
                        wording.wording.fill_badge(
                            user['post_'],
                            user['name'],
                            user['caption']
                        )
                    badges_filepaths = [file for file in os.listdir(f"{current_directory}/wording/generated") if file.startswith('badge_')]

                    def chunked_iterable(iterable, size):
                        it = iter(iterable)
                        return iter(lambda: list(islice(it, size)), [])

                    chunks = list(chunked_iterable(badges_filepaths, 8))

                    final_badges = []
                    for index, chunk in enumerate(chunks):
                        filepath = f"{current_directory}/wording/generated/badges_list_{index}.png"
                        final_badges.append(filepath)
                        wording.wording.create_badge_sheet(
                            final_file_name=filepath,
                            insert_paths=chunk
                        )

                    pdf_filename = f"{current_directory}/wording/generated/badges_all_{datetime.datetime.now().strftime('%Y_%m_%d')}.pdf"
                    wording.wording.images_to_pdf(filepath_list=final_badges, output_filename=pdf_filename)

                    caption += "Набор бейджей"

                    if send_telegram_document(
                            tID=response['telegram_id'],
                            filepath=pdf_filename,
                            description=caption + "\n\n#документы"
                    ):
                        open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                    else:
                        open_sb("Ошибка Telegram", ft.colors.RED)

                    if os.path.exists(pdf_filename):
                        os.remove(pdf_filename)

                    for filepath in badges_filepaths:
                        if os.path.exists(f"{current_directory}/wording/generated/{filepath}"):
                            os.remove(f"{current_directory}/wording/generated/{filepath}")

                    for filepath in final_badges:
                        if os.path.exists(filepath):
                            os.remove(filepath)

        pdf_filepaths.clear()
        dlg_loading.close()

    def get_document_card(title: str, sb: str, icon: ft.icons, doctype: str):

        card = ft.ListTile(
            title=ft.Text(title),
            subtitle=ft.Text(sb),
            leading=ft.Icon(icon),
            data={'doctype': doctype},
            on_click=generate_document
        )

        return card

    def open_popup(e: ft.ControlEvent):
        target = e.control.data['target']

        if target == 'modules_info':
            module_record_open = load_config_file('config.json')['module_record']
            if module_record_open:
                module_record_tile = ft.ListTile(
                    title=ft.Text('Закрыть запись'),
                    subtitle=ft.Text('Закрытие записи на образовательные модули'),
                    leading=ft.Icon(ft.icons.BOOK, color=ft.colors.RED),
                    on_click=lambda _: open_confirmation("stop_modules")
                )
            else:
                module_record_tile = ft.ListTile(
                    title=ft.Text('Открыть запись'),
                    subtitle=ft.Text('Открытие записи на образовательные модули'),
                    leading=ft.Icon(ft.icons.BOOK, color=ft.colors.AMBER),
                    on_click=lambda _: open_confirmation("start_modules")
                )

            controls = [
                ft.ListTile(
                    title=ft.Text('Создать модуль'),
                    leading=ft.Icon(ft.icons.CREATE_NEW_FOLDER, color=ft.colors.GREEN),
                    on_click=lambda _: change_screen("create_module")
                ),
                module_record_tile,
                ft.Divider(thickness=1),
                ft.ListTile(
                    title=ft.Text('Удалить модули'),
                    subtitle=ft.Text('Полное удаление информации о текущих модулях'),
                    leading=ft.Icon(ft.icons.DELETE_SWEEP, color=ft.colors.RED),
                    on_click=lambda _: open_confirmation("remove_modules")
                ),
                ft.ListTile(
                    title=ft.Text('Удалить записи'),
                    subtitle=ft.Text('Удаление информации об участниках модулей'),
                    leading=ft.Icon(ft.icons.GROUP_REMOVE, color=ft.colors.RED),
                    on_click=lambda _: open_confirmation("remove_modules_records")
                )
            ]

        elif target == 'reboot_menu':
            controls = [
                ft.ListTile(
                    title=ft.Text('Перезагрузить сервер'),
                    subtitle=ft.Text('Остановка всех сервисов и перезапуск сервера'),
                    leading=ft.Icon(ft.icons.DEVELOPER_BOARD, ft.colors.AMBER),
                    on_click=lambda _: open_confirmation("reboot_server")
                ),
            ]

        bottom_sheet.content = ft.Column(controls=controls, scroll=ft.ScrollMode.AUTO)
        bottom_sheet.height = 500
        bottom_sheet.open()

    def show_module_info(e: ft.ControlEvent):
        data = e.control.data
        module, teacher = data['module'], data['teacher']

        dlg_info.title = ""
        dlg_info.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Информация о модуле", size=16, weight=ft.FontWeight.W_200),
                    ft.ListTile(
                        title=ft.Text(module['name'], size=16),
                        subtitle=ft.Text(teacher['name'], size=14),
                        leading=ft.Icon(ft.icons.ARTICLE)
                    ),
                    ft.ListTile(
                        title=ft.Text(module['location'], size=16),
                        subtitle=ft.Text(f"Занято {module['seats_real']} из {module['seats_max']} мест", size=14),
                        leading=ft.Icon(ft.icons.LOCATION_ON)
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                width=600,
                height=250
            ),
            padding=ft.padding.all(-15)
        )
        dlg_info.open()

    def set_current_shift(e: ft.ControlEvent):
        config = load_config_file('config.json')
        config['shift']['current_shift'] = e.control.data['shift_index']
        update_config_file(config, 'config.json')
        bottom_sheet.close()
        change_screen("main")
        reboot_systemd('crod_connect_bot')

    def change_current_shift(e: ft.ControlEvent):
        shift_list = load_config_file('config.json')['shift']['shift_list']

        shifts_col = ft.Column()
        for index, shift in enumerate(shift_list):
            start_date, end_date = convert_date(shift['date']['start']), convert_date(shift['date']['end'])

            shifts_col.controls.append(
                ft.Container(
                    ft.ListTile(
                        title=ft.Text(shift['name'], size=18),
                        subtitle=ft.Text(f"{start_date} - {end_date}", size=14),
                        data={'shift_index': index},
                        on_click=set_current_shift
                    ),
                )
            )
        bottom_sheet.content = ft.Column(
            [
                ft.Text(f"\nВыберите смену или поток", size=16, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER),
                shifts_col
            ],
            width=600,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        bottom_sheet.height = 1000
        bottom_sheet.open()

    def change_screen(target: str):
        logging.info(f"Changing screen to: {target}")

        bottom_sheet.close()
        page.controls.clear()
        page.appbar.visible = False
        page.appbar.actions.clear()
        page.scroll = screens[target]['scroll_mode']

        if screens[target]['appbar']['visible']:
            page.appbar.visible = True
            leading_icon = screens[target]['appbar']['leading']['icon']
            action = screens[target]['appbar']['leading']['action']
            if action == "change_screen":
                page.appbar.leading = ft.IconButton(
                    icon=leading_icon,
                    on_click=lambda _: change_screen(screens[target]['appbar']['leading']['target'])
                )
            elif action == "drawer":
                page.appbar.leading = ft.IconButton(
                    icon=leading_icon,
                    on_click=open_menu_drawer
                )
            elif action is None:
                page.appbar.leading = ft.Icon(leading_icon)

            page.appbar.title.value = screens[target]['appbar']['title']

        if target == "login":
            page.add(ft.Container(login_col, expand=True))

        elif target == "main":
            shift = load_config_file('config.json')['shift']
            current_shift_info = shift['shift_list'][shift['current_shift']]
            query = "SELECT * FROM crodconnect.admins WHERE password = %s"
            admin = make_db_request(query, (password_field.value,))

            systemd_pb = ft.ProgressBar()

            systemd_text = ft.Text(size=16)
            systemd_btn = ft.FilledTonalButton(text="Перезагрузка", icon=ft.icons.RESTART_ALT, on_click=lambda _: change_screen("reboot_menu"), visible=False)
            systemd_card = ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.SETTINGS_INPUT_ANTENNA),
                                    ft.Text("Состояние системы", size=20, weight=ft.FontWeight.W_400)
                                ]
                            ),
                            systemd_pb,
                            systemd_text,
                            systemd_btn
                        ]
                    ),
                    padding=15
                ),
                width=600
            )

            shift_info_col = ft.Column()

            if datetime.datetime.strptime(current_shift_info['date']['start'], '%Y-%m-%d') <= datetime.datetime.now() <= datetime.datetime.strptime(current_shift_info['date']['end'], '%Y-%m-%d'):
                shift_info_col.controls = [
                    ft.Container(
                        ft.Column(
                            [
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Текущая смена/поток", size=14),
                                        subtitle=ft.Text(current_shift_info['name'], size=16, weight=ft.FontWeight.W_400)
                                    ),
                                    padding=ft.padding.only(bottom=-30)
                                ),
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Дата начала", size=14),
                                        subtitle=ft.Text(convert_date(current_shift_info['date']['start']), size=16, weight=ft.FontWeight.W_400)
                                    ),
                                    padding=ft.padding.only(bottom=-30)
                                ),
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Дата окончания", size=14),
                                        subtitle=ft.Text(convert_date(current_shift_info['date']['end']), size=16, weight=ft.FontWeight.W_400)
                                    )
                                )
                            ]
                        ),
                        padding=ft.padding.only(left=-15)
                    ),
                ]
            else:
                shift_info_col.controls = [
                    ft.Text("Активная смена или поток отсутствует", size=16),
                    ft.Container(
                        ft.Column(
                            [
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Предстоящая смена/поток", size=14),
                                        subtitle=ft.Text(current_shift_info['name'], size=16, weight=ft.FontWeight.W_400)
                                    ),
                                    padding=ft.padding.only(bottom=-30)
                                ),
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Дата начала", size=14),
                                        subtitle=ft.Text(convert_date(current_shift_info['date']['start']), size=16, weight=ft.FontWeight.W_400)
                                    ),
                                    padding=ft.padding.only(bottom=-30)
                                ),
                                ft.Container(
                                    ft.ListTile(
                                        title=ft.Text("Дата окончания", size=14),
                                        subtitle=ft.Text(convert_date(current_shift_info['date']['end']), size=16, weight=ft.FontWeight.W_400)
                                    )
                                )
                            ]
                        ),
                        padding=ft.padding.only(left=-15)
                    )
                ]

            shift_info_col.controls.append(
                ft.FilledTonalButton(
                    text="Изменить",
                    icon=ft.icons.EDIT,
                    on_click=change_current_shift
                )

            )

            current_shift_info = ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.INFO),
                                    ft.Text("Общая информация", size=20, weight=ft.FontWeight.W_400)
                                ]
                            ),
                            shift_info_col
                        ]
                    ),
                    padding=15
                ),
                width=600
            )

            col = ft.Column(
                controls=[
                    ft.Container(ft.Text(get_hello(admin['name'].split()[1]), size=25, weight=ft.FontWeight.W_600), padding=ft.padding.only(left=10)),
                    systemd_card,
                    current_shift_info
                ]
            )

            page.add(col)
            page.update()

            systemd_list = get_system_list()
            if systemd_list:
                systemd_card.surface_tint_color = ft.colors.RED
                systemd_text.value = "Обнаружены нерабочие сервисы"
                systemd_btn.visible = True
            else:
                systemd_card.surface_tint_color = ft.colors.GREEN
                systemd_text.value = "Все сервисы работают корректно"
                systemd_btn.visible = False

            systemd_pb.visible = False
            page.update()

        elif target == "edit_env":
            with open(env_path, "r") as f:
                env_data = f.readlines()
            env_field.value = "".join(env_data)

            col = ft.Column(
                controls=[
                    env_field,
                    ft.FilledTonalButton(
                        text="Сохранить",
                        icon=ft.icons.SAVE_ALT,
                        on_click=update_env
                    )
                ]
            )
            page.add(col)

        elif target == "extra_users":
            extra_users.clear()
            extra_users.add_user()
            page.add(extra_users.users_col)

        elif target == "modules_info":
            page.appbar.actions = [
                ft.Container(
                    ft.Row(
                        [
                            ft.IconButton(icon=ft.icons.RESTART_ALT, on_click=lambda _: change_screen("modules_info"), tooltip="Обновить"),
                            ft.IconButton(
                                icon=ft.icons.APPS,
                                on_click=open_popup,
                                data={'target': 'modules_info'}
                            ),
                        ]
                    ),
                    padding=ft.padding.only(right=10)
                )
            ]
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()

            query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
            admins_list = make_db_request(query)
            if admins_list is not None:
                if type(admins_list) == dict: admins_list = [admins_list]
                col = ft.ResponsiveRow(columns=3)
                for admin in admins_list:
                    query = "SELECT * FROM crodconnect.teachers WHERE module_id = %s"
                    teacher_info = make_db_request(query, (admin['id'],))
                    if teacher_info is not None:
                        popup_items = [
                            ft.FilledButton(text='Изменить локацию', icon=ft.icons.LOCATION_ON, on_click=show_qr,
                                            data={'phrase': f"teachers_{teacher_info['pass_phrase']}", 'caption': teacher_info['name']}),
                            ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data={'phrase': f"teachers_{teacher_info['pass_phrase']}", 'caption': teacher_info['name']}),
                            ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=teacher_info['pass_phrase'], on_click=goto_remove_module),
                        ]

                        card = ft.Card(
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    ft.ListTile(
                                                        title=ft.Text(admin['name'], size=16),
                                                        subtitle=ft.Text(teacher_info['name'], size=14),
                                                        leading=ft.Icon(
                                                            ft.icons.ARTICLE,
                                                            color=user_statuses[teacher_info['status']]['color'],
                                                            tooltip=user_statuses[teacher_info['status']]['naming']
                                                        )
                                                    ),
                                                    expand=True
                                                ),
                                                ft.PopupMenuButton(
                                                    items=popup_items
                                                )
                                            ]
                                        ),
                                        ft.ListTile(
                                            # title=ft.Text('Локация', size=14),
                                            title=ft.Text(admin['location'], size=16),
                                            subtitle=ft.Text(f"{admin['seats_real']} из {admin['seats_max']}", size=14),
                                            leading=ft.Icon(ft.icons.LOCATION_ON)
                                        ),
                                    ],
                                    spacing=0.5
                                ),
                                padding=ft.padding.only(top=15, bottom=15)
                            ),
                            width=600,
                            col={"lg": 1}
                        )
                        col.controls.append(card)
                if not admins_list:
                    col.controls.append(
                        ft.Row([ft.FilledTonalButton(text='Создать модуль', icon=ft.icons.CREATE_NEW_FOLDER, on_click=lambda _: change_screen('create_module'))], alignment=ft.MainAxisAlignment.CENTER)
                    )
                page.add(col)
                dlg_loading.close()

        elif target == "edit_child_group_num":
            query = "SELECT * FROM crodconnect.children"
            data = make_db_request(query)
            if db.result['status'] == "ok":
                if type(data) == dict: data = [data]
                page.session.set('children_list', data)
                col = ft.Column(
                    controls=[
                        ft.TextField(
                            label="ФИО ребёнка",
                            prefix_icon=ft.icons.CHILD_CARE,
                            hint_text="Иванов Иван Иванович",
                            on_change=find_child
                        ),
                        child_col
                    ],
                    width=600
                )
                page.add(col)

        elif target == "add_child":
            new_child.reset()
            col = ft.Column(
                controls=[
                    new_child.name,
                    ft.Row([new_child.birth_day, new_child.birth_month, new_child.birth_year]),
                    new_child.group,
                    new_child.caption,
                    ft.Divider(thickness=1),
                    new_child.parent_name,
                    new_child.phone,
                    ft.Row([btn_add_child], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "create_mentor":
            new_mentor.reset()
            col = ft.Column(
                controls=[
                    new_mentor.name,
                    new_mentor.group,
                    ft.Row([btn_add_mentor], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))

        elif target == "create_admin":
            new_admin.reset()
            col = ft.Column(
                controls=[
                    new_admin.name,
                    new_admin.post,
                    ft.Row([new_admin.panel_access, ft.Text("доступ к панели", size=16, weight=ft.FontWeight.W_200)]),
                    ft.Row([btn_add_admin], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))

        elif target == "mentors_info":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.PERSON_ADD, on_click=lambda _: change_screen("create_mentor")),
                    padding=10
                )
            ]
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()
            query = "SELECT * FROM crodconnect.mentors"
            mentors_list = make_db_request(query)
            if mentors_list is not None:
                col = ft.Column()
                for mentor in mentors_list:
                    popup_items = [
                        ft.FilledButton(text='Изменить группу', icon=ft.icons.EDIT, on_click=goto_change_mentor_group, data=mentor['pass_phrase']),
                        ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data={'phrase': f"mentors_{mentor['pass_phrase']}", 'caption': mentor['name']}),
                        ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=mentor['pass_phrase'], on_click=remove_mentor),
                    ]

                    if mentor['status'] == 'active':
                        popup_items.insert(0, ft.FilledButton(text='Отключить', icon=ft.icons.BLOCK, on_click=change_active_status, data=f"mentors_{mentor['pass_phrase']}_frozen"), )
                    elif mentor['status'] == 'frozen':
                        popup_items.insert(0, ft.FilledButton(text='Активировать', icon=ft.icons.ADD, on_click=change_active_status, data=f"mentors_{mentor['pass_phrase']}_active"), )

                    col.controls.append(
                        ft.Card(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Container(
                                            ft.ListTile(
                                                title=ft.Text(mentor['name']),
                                                subtitle=ft.Text(f"Группа №{mentor['group_num']}"),
                                                leading=ft.Icon(
                                                    ft.icons.ACCOUNT_CIRCLE,
                                                    color=user_statuses[mentor['status']]['color'],
                                                    tooltip=user_statuses[mentor['status']]['naming']
                                                )
                                            ),
                                            expand=True
                                        ),
                                        ft.PopupMenuButton(
                                            items=popup_items
                                        )
                                    ]
                                ),
                                padding=ft.padding.only(right=10)
                            ),
                            width=600
                        )
                    )
                page.add(col)
                dlg_loading.close()

        elif target == "admins_info":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.PERSON_ADD, on_click=lambda _: change_screen("create_admin")),
                    padding=10
                )
            ]
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()
            query = "SELECT * FROM crodconnect.admins WHERE status != 'creator'"
            admins_list = make_db_request(query)
            if type(admins_list) == dict: admins_list = [admins_list]

            if admins_list is not None:
                col = ft.Column()
                for admin in admins_list:
                    popup_items = [
                        ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data={'phrase': f"admins_{admin['pass_phrase']}", 'caption': admin['name']}),
                        ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=admin['pass_phrase'], on_click=remove_admin),
                    ]

                    if admin['status'] == 'active':
                        popup_items.insert(0, ft.FilledButton(text='Отключить', icon=ft.icons.BLOCK, on_click=change_active_status, data=f"admins_{admin['pass_phrase']}_frozen"))
                    elif admin['status'] == 'frozen':
                        popup_items.insert(0, ft.FilledButton(text='Активировать', icon=ft.icons.ADD, on_click=change_active_status, data=f"admins_{admin['pass_phrase']}_active"))

                    if admin['password'] == password_field.value:
                        popup_items = None
                    col.controls.append(
                        ft.Card(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Container(
                                            ft.ListTile(
                                                title=ft.Text(admin['name']),
                                                subtitle=ft.Text(f"{admin['post']}"),
                                                leading=ft.Icon(
                                                    ft.icons.ACCOUNT_CIRCLE,
                                                    color=user_statuses[admin['status']]['color'],
                                                    tooltip=user_statuses[admin['status']]['naming']
                                                )
                                            ),
                                            expand=True
                                        ),
                                        ft.PopupMenuButton(
                                            items=popup_items
                                        )
                                    ]
                                ),
                                padding=ft.padding.only(right=10)
                            ),
                            width=600
                        )
                    )
                page.add(col)
                dlg_loading.close()

        elif target == "documents":
            col = ft.Column(
                controls=[
                    get_document_card(
                        title="Списки групп",
                        sb="Таблицы с особенностями детей и контактами родителей",
                        icon=ft.icons.VIEW_LIST,
                        doctype='groups'
                    ),
                    get_document_card(
                        title="QR-коды",
                        sb="Таблицы с QR-кодами для групп, воспитателей и преподавателей",
                        icon=ft.icons.QR_CODE_2,
                        doctype='qr'
                    ),
                    get_document_card(
                        title="Списки модулей",
                        sb="Распределение детей по учебным модулям",
                        icon=ft.icons.GROUPS,
                        doctype='modules'
                    ),
                    get_document_card(
                        title="Навигация",
                        sb="Распределение модулей по аудиториям",
                        icon=ft.icons.LOCATION_ON,
                        doctype='navigation'
                    ),
                    get_document_card(
                        title="Бейджики",
                        sb="Создание бейджей для всех участников",
                        icon=ft.icons.BADGE,
                        doctype='badge'
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=600
            )
            page.add(col)

        elif target == "create_module":
            new_module.reset()

            col = ft.Column(
                controls=[
                    new_module.module_name,
                    new_module.teacher_name,
                    new_module.locations_dropdown,
                    new_module.seats_count,
                    ft.Row([btn_add_module], alignment=ft.MainAxisAlignment.END)
                ],
                width=600
            )
            page.add(col)

        elif target == "reboot_menu":
            page.appbar.actions = [
                ft.Container(
                    ft.Row(
                        [
                            ft.IconButton(icon=ft.icons.RESTART_ALT, on_click=lambda _: change_screen("reboot_menu"), tooltip="Обновить"),
                            ft.IconButton(
                                icon=ft.icons.APPS,
                                on_click=open_popup,
                                data={'target': 'reboot_menu'}
                            )
                        ]
                    ),
                    padding=ft.padding.only(right=10)
                )
            ]

            dlg_loading.loading_text = "Обновляем"
            dlg_loading.open()

            col = ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.icons.CIRCLE, color=ft.colors.GREEN), ft.Text("доступно"), ft.Icon(ft.icons.CIRCLE, color=ft.colors.RED), ft.Text("требуется перезагрузка")],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

            for service in services_list:
                col.controls.append(
                    get_reboot_card(
                        title=service['title'],
                        icon=ft.icons.ADD_TASK,
                        target=service['service']
                    )
                )

            page.add(col)
            dlg_loading.close()

        elif target == "module_check":
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()
            time.sleep(0.5)

            module_check_info = page.session.get('modulecheck_info')
            module = module_check_info['module']

            query = "SELECT * FROM crodconnect.teachers WHERE module_id = %s LIMIT 1"
            teacher_info = make_db_request(query, (module['id'],))
            if db.result['status'] == 'ok':
                page.appbar.actions = [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    ft.icons.INFO_OUTLINED,
                                    data={'module': module, 'teacher': teacher_info},
                                    on_click=show_module_info
                                )
                            ]
                        ),
                        padding=ft.padding.only(right=10)
                    )
                ]

            query = "SELECT * FROM crodconnect.children WHERE id IN (SELECT child_id FROM crodconnect.modules_records WHERE module_id = %s)"

            children_list = make_db_request(query, (module['id'],))
            if db.result['status'] == 'ok':
                if type(children_list) == dict: children_list = [children_list]

                if len(children_list) > 0:
                    page.controls.clear()
                    module_traffic_col.controls.clear()

                    for child in children_list:
                        remaining_children_traffic.append(child)
                        module_traffic_col.controls.append(
                            ft.Row(
                                [
                                    ft.Container(ft.Text(child['name'], size=16, weight=ft.FontWeight.W_200, width=300), expand=True),
                                    ft.Checkbox(data=child, on_change=modulecheck_checkbox_changed)
                                ]
                            )
                        )

                    module_traffic_col.controls.append(
                        ft.Row(
                            [
                                ft.FilledButton(text="Сохранить", icon=ft.icons.SAVE, on_click=lambda _: update_modulecheck())
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    )

                    page.add(module_traffic_col)

                else:
                    change_screen("module_check_start")
                    dlg_info.title = "Посещаемость"
                    dlg_info.content = ft.Text(f"На модуль «{module['name']}» пока никто не записан.", size=16, weight=ft.FontWeight.W_200)
                    dlg_info.open()

            dlg_loading.close()

        elif target == "module_check_start":
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()
            time.sleep(0.5)

            query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
            modules_list = make_db_request(query)
            if db.result['status'] == 'ok':
                if type(modules_list) == dict: modules_list = [modules_list]

                if len(modules_list) > 0:
                    modules_col = ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=600
                    )

                    for module in modules_list:
                        modules_col.controls.append(
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.ListTile(
                                                title=ft.Text(module['name']),
                                                subtitle=ft.Text(module['location']),
                                            ),
                                            expand=True
                                        ),
                                        ft.Container(ft.Icon(ft.icons.ARROW_FORWARD_IOS), padding=ft.padding.only(right=15))
                                    ]
                                ),
                                data={'module': module},
                                on_click=goto_modulecheck
                            )

                        )

                    page.add(modules_col)

                else:
                    dlg_info.title = "Посещаемость"
                    dlg_info.content = ft.Text("Не найдено активных образовательных модулей.", size=16, weight=ft.FontWeight.W_200)
                    dlg_info.open()

            dlg_loading.close()

        elif target == "select_qr_group":
            col = ft.Column(
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.FILTER_1),
                        title=ft.Text("Группа №1"),
                        on_click=lambda _: get_showqr('children', '1', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.FILTER_2),
                        title=ft.Text("Группа №2"),
                        on_click=lambda _: get_showqr('children', '2', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.FILTER_3),
                        title=ft.Text("Группа №3"),
                        on_click=lambda _: get_showqr('children', '3', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.FILTER_4),
                        title=ft.Text("Группа №4"),
                        on_click=lambda _: get_showqr('children', '4', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.FILTER_5),
                        title=ft.Text("Группа №5"),
                        on_click=lambda _: get_showqr('children', '5', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.EMOJI_PEOPLE),
                        title=ft.Text("Воспитатели"),
                        on_click=lambda _: get_showqr('mentors', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.MANAGE_ACCOUNTS),
                        title=ft.Text("Администрация"),
                        on_click=lambda _: get_showqr('admins', admin=True)
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.SCHOOL),
                        title=ft.Text("Преподаватели"),
                        on_click=lambda _: get_showqr('teachers', admin=True)
                    ),
                ],
                width=600,
                # scroll=ft.ScrollMode.HIDDEN
            )
            page.add(col)

        elif target == "app_info":
            col = ft.Column(
                controls=[
                    ft.Card(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Image(
                                        src='icons/loading-animation.png',
                                        height=100,
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            padding=10
                        )
                    ),
                    ft.Column(
                        [
                            ft.Text("ЦРОД.Коннект (v1.0)", size=20, weight=ft.FontWeight.W_400),
                            ft.Text("Приложение для автоматизации процессов во время летних смен и учебных потоков в Центре развития одарённых детей", size=16, text_align=ft.TextAlign.START,
                                    width=500, weight=ft.FontWeight.W_200),
                            ft.Container(ft.Divider(thickness=1), width=200),
                            ft.FilledTonalButton("Связаться с разработчиком", url="https://t.me/lrrrtm", icon=ft.icons.MANAGE_ACCOUNTS)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=1
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))

        page.update()

    btn_add_child = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_child()
    )

    btn_add_mentor = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_mentor()
    )

    btn_add_admin = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_admin()
    )

    btn_add_module = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_module()
    )

    new_module = NewModule(page=page, save_btn=btn_add_module)
    new_admin = NewAdmin(page=page, save_btn=btn_add_admin)
    new_mentor = NewMentor(page=page, save_btn=btn_add_mentor)
    new_child = NewChild(page=page, save_btn=btn_add_child)
    extra_users = ExtraUsers(page=page)

    def change_active_status(e: ft.ControlEvent):
        data = e.control.data.split("_")
        target = data[0]
        pass_phrase = data[1]
        status = data[2]

        query = f"UPDATE {target} SET status = %s WHERE pass_phrase = %s"
        if make_db_request(query, (status, pass_phrase,)) is not None:
            open_sb("Статус изменён", ft.colors.GREEN)
            change_screen(f"{target}_info")

    def upload_tables(e):
        if cildren_table_picker.result is not None and cildren_table_picker.result.files is not None:
            file = cildren_table_picker.result.files[0]
            upload_list = [
                ft.FilePickerUploadFile(
                    name=file.name,
                    upload_url=page.get_upload_url(file.name, 600),
                )
            ]

            dlg_loading.loading_text = "Загружаем файл"
            dlg_loading.open()

            cildren_table_picker.upload(upload_list)
            time.sleep(2)

            dlg_loading.close()
            open_sb("Файл загружен", ft.colors.GREEN)
            insert_children_info(f'assets/uploads/{file.name}')

        else:
            open_sb("Загрузка отменена")

    cildren_table_picker = ft.FilePicker(on_result=upload_tables)
    page.overlay.append(cildren_table_picker)

    def password_confirmed():
        bottom_sheet.close()
        action = bottom_sheet.sheet.data[1]
        if action == "upload_children":
            cildren_table_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=['xls', 'xlsx']
            )

        elif action == "edit_stream":
            change_screen("edit_env")

        elif action == "start_modules":
            dlg_info.title = "Учебные модули"
            dlg_info.content = ft.Text(
                "Запись на учебные модули откроется в течение 1 минуты.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open()
            config = load_config_file('config.json')
            config['module_record'] = True
            update_config_file(config, 'config.json')

        elif action == "stop_modules":
            dlg_info.title = "Учебные модули"
            dlg_info.content = ft.Text(
                "Запись на учебные модули закроется в течение 1 минуты.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open()
            config = load_config_file('config.json')
            config['module_record'] = False
            update_config_file(config, 'config.json')

        elif action == "remove_modules":
            mysql_backup()
            dlg_loading.loading_text = "Удаляем модули"
            dlg_loading.open()

            query = "TRUNCATE TABLE crodconnect.modules_records"
            make_db_request(query)

            query = "TRUNCATE TABLE crodconnect.teachers"
            make_db_request(query)

            query = "TRUNCATE TABLE crodconnect.modules"
            if make_db_request(query) is not None:
                open_sb("Учебные модули удалены", ft.colors.GREEN)

            change_screen("modules_info")
            dlg_loading.close()

        elif action == "remove_module":
            mysql_backup()
            remove_module(page.session.get('remove_module_pass_phrase'))

        elif action == "remove_modules_records":
            mysql_backup()
            dlg_loading.loading_text = "Удаляем записи"
            dlg_loading.open()

            query = "TRUNCATE TABLE crodconnect.modules_records"
            make_db_request(query)

            query = "UPDATE crodconnect.modules SET seats_real = 0"
            if make_db_request(query) is not None:
                open_sb("Записи на модули удалены", ft.colors.GREEN)

            change_screen("modules_info")
            dlg_loading.close()

        elif action == "reboot_server":
            dlg_info.title = "Перезагрузка сервера"
            dlg_info.content = ft.Text(
                "Запрос на перезагрузку сервера отправлен. Все сервисы будут недоступны в течение нескольких минут.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open()
            if platform.system() == "Linux":
                subprocess.run("sudo reboot", shell=True)

        elif action == "admin_show_qrlist":
            change_screen("select_qr_group")

        if page.session.get('confirmation_data') is not None:
            delete_telegram_message(page.session.get('confirmation_data'))

    def open_confirmation(action: str, type: str = 'simple', tid=None):
        bottom_sheet.close()
        actions_descrition = {
            'upload_children': {
                'title': "Обновление списка детей"
            },
            'edit_stream': {
                'title': "Доступ к конфигурации"
            },
            'remove_modules': {
                'title': "Удаление модулей"
            },
            'remove_module': {
                'title': "Удаление модуля"
            },
            'remove_modules_records': {
                'title': "Удаление записей на модули"
            },
            'reboot_server': {
                'title': "Перезагрузка сервера"
            },
            'admin_show_qrlist': {
                'title': "QR-коды"
            },
            'start_modules': {
                'title': "Открытие записи на модули"
            }
            ,
            'stop_modules': {
                'title': "Закрытие записи на модули"
            }
        }

        confirmation_code = random.randint(111111, 999999)
        bottom_sheet.sheet.data = [confirmation_code, action]
        pswd_field = ConfirmationCodeField(page=page, true_password=confirmation_code, func=password_confirmed)

        bottom_sheet.content = ft.Column(
            [
                ft.Text(f"{actions_descrition[action]['title']}\nОтправили код в Telegram", size=16, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER),
            ],
            width=600,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        bottom_sheet.height = 300

        if type == 'simple':
            if is_telegrammed('confirm'):
                bottom_sheet.open()
                id = password_field.data['telegram_id']
            else:
                return

        elif type == 'telegram':
            bottom_sheet.open()

            id = tid

        data = send_telegam_message(
            id,
            f"\n\nВаш код подтверждения: `{confirmation_code}`"
        )
        if data:
            page.session.set('confirmation_data', data)

        pswd_field.create(target=bottom_sheet.content)

    def goto_update_service(e: ft.ControlEvent):
        bottom_sheet.close()

        service = e.control.data
        open_sb(f"Обновляем {service}")

        result = make_update(service)
        dlg_info.title = "Обновление"
        dlg_info.content = ft.Text(
            result['msg'],
            width=600, size=16, weight=ft.FontWeight.W_200
        )
        dlg_info.open()

    def login():
        if password_field.value.strip() == "remote@update":
            password_field.value = ''

            col = ft.Column(
                [
                    ft.Text("Выберите сервис для обновления", size=16, weight=ft.FontWeight.W_200),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=600
            )

            for service in services_list:
                col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.ANDROID),
                        title=ft.Text(service['title']),
                        data=service['service'],
                        on_click=goto_update_service
                    )
                )

            bottom_sheet.content = col
            bottom_sheet.open()

        query = "SELECT * FROM crodconnect.admins WHERE password = %s"
        admin_info = make_db_request(query, (password_field.value,))
        if db.result['status'] == 'ok':
            if not admin_info:
                open_sb("Ошибка доступа", ft.colors.RED)
            else:
                if admin_info['status'] in ['active', 'creator'] and bool(admin_info['access']):
                    password_field.data = admin_info
                    change_screen("main")

                elif not bool(admin_info['access']):
                    password_field.value = ''
                    dlg_info.title = "Авторизация"
                    dlg_info.content = ft.Text(
                        "У вас недостаточно прав для доступа к панели управления. Если вы считаете, что произошла ошибка, то обратитесь к администрации.",
                        width=600, size=16, weight=ft.FontWeight.W_200
                    )
                    dlg_info.open()

                elif admin_info['status'] == 'waiting_for_registration':
                    password_field.value = ''

                    bottom_sheet.content = ft.Column(
                        [
                            ft.Text(
                                "Чтобы продолжить, зарегистрируйтесь в Telegram-боте",
                                width=600, size=16, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER
                            ),
                            ft.FilledButton(
                                text="Зарегистрироваться", icon=ft.icons.TELEGRAM, url=f"https://t.me/{os.getenv('BOT_NAME')}?start=admins_{admin_info['pass_phrase']}",
                                on_click=lambda _: bottom_sheet.close(), style=ft.ButtonStyle(bgcolor="#2aabee", color=ft.colors.WHITE)
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                    bottom_sheet.height = 100
                    bottom_sheet.open()

                elif admin_info['status'] == 'frozen':
                    password_field.value = ''
                    dlg_info.title = "Авторизация"
                    dlg_info.content = ft.Text(
                        "Ваш аккаунт деактивирован, поэтому вы не можете получить доступ к панели управления. Если вы считаете, что произошла ошибка, то обратитесь к администрации.",
                        width=600, size=16, weight=ft.FontWeight.W_200
                    )
                    dlg_info.open()

        page.update()

    page.appbar = ft.AppBar(
        center_title=False,
        title=ft.Text(size=20, weight=ft.FontWeight.W_500)
        # bgcolor=ft.colors.SURFACE_VARIANT
    )

    module_traffic_col = ft.Column(width=600, scroll=ft.ScrollMode.HIDDEN)

    password_field = ft.TextField(
        label="Код доступа", text_align=ft.TextAlign.CENTER,
        width=250,
        height=70,
        on_submit=lambda _: login(),
        password=True
    )

    button_login = ft.FilledButton("Войти", width=250, on_click=lambda _: login(),
                                   disabled=False, height=50,
                                   icon=ft.icons.KEYBOARD_ARROW_RIGHT_ROUNDED)

    login_col = ft.Column(
        controls=[
            ft.Image(
                src='icons/loading-animation.png',
                height=200,
            ),
            password_field,
            button_login
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    # Диалоги

    env_field = ft.TextField(
        multiline=True
    )

    # Функции
    def update_env(e: ft.ControlEvent):
        env_data = env_field.value
        with open(env_path, "w") as f:
            f.write(env_data)

        dlg_info.title = "Конфигурация"
        dlg_info.content = ft.Text(
            "Конфигурационный файл обновлён. Чтобы изменения вступили в силу, перезагрузите необходимые элементы системы.",
            width=600, size=16, weight=ft.FontWeight.W_200
        )
        change_screen("reboot_menu")
        dlg_info.open()

    def open_dialog(dialog: ft.AlertDialog):
        page.dialog = dialog
        dialog.open = True
        page.update()

        # if dialog == dialog_loading:
        #     time.sleep(1)

    def close_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        page.update()

    def open_sb(text: str, bgcolor=ft.colors.WHITE):
        if bgcolor != ft.colors.WHITE:
            text_color = ft.colors.WHITE
        else:
            text_color = ft.colors.BLACK

        content = ft.Text(text, size=18, text_align=ft.TextAlign.START, weight=ft.FontWeight.W_300, color=text_color)
        page.snack_bar = ft.SnackBar(
            content=content,
            duration=1200,
            bgcolor=bgcolor
        )
        page.snack_bar.open = True
        page.update()

    def modulecheck_checkbox_changed(e: ft.ControlEvent):
        if e.control.value:
            remaining_children_traffic.remove(e.control.data)
        else:
            remaining_children_traffic.append(e.control.data)

    def update_modulecheck():

        module_check_info = page.session.get('modulecheck_info')
        print(module_check_info)
        module, mentor = module_check_info['module'], module_check_info['mentor']

        if remaining_children_traffic:
            text = ""
            module_traffic_col.controls.clear()
            for child in remaining_children_traffic:
                module_traffic_col.controls.append(
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(ft.Text(child['name'], size=16, weight=ft.FontWeight.W_200, width=300), expand=True),
                                ft.Checkbox(data=child, on_change=modulecheck_checkbox_changed)
                            ]
                        )
                    )
                )
                text += f"({child['group_num']}) {child['name']}\n"

            module_traffic_col.controls.append(
                ft.Row(
                    [
                        ft.FilledButton(text="Сохранить", icon=ft.icons.SAVE, on_click=lambda _: update_modulecheck())
                    ],
                    alignment=ft.MainAxisAlignment.END
                )
            )
            open_sb(f"Осталось отметить: {len(remaining_children_traffic)}")
            message_text = f"\n\n*Посещаемость «{module['name']}»*" \
                           f"\n\n⚠️ Пришли не все:\n" \
                           f"{text}" \
                           f"\n*🕵️ {mentor['name']}*"

        else:
            page.controls.clear()
            dlg_info.title = "Посещаемость"
            dlg_info.content = ft.Text(
                "Все дети на месте, спасибо! Можно возвращаться в Telegram.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open(action_btn_visible=False)

            message_text = f"\n\n*Посещаемость «{module['name']}»*" \
                           f"\n\n✅ Все дети на месте" \
                           f"\n\n🕵️ {mentor['name']}"

        send_telegam_message(os.getenv('ID_GROUP_MAIN'), message_text)
        page.update()

    def copy_qr_link(link):
        # копирование пригласительной ссылки

        page.set_clipboard(link)
        bottom_sheet.close()
        open_sb("Ссылка скопирована")

    def get_user_qr(e: ft.ControlEvent):
        data = e.control.data
        show_qr({'phrase': f"{data['status']}_{data['pass_phrase']}", 'caption': data['name']})

    def show_qr(e):
        # показ диалога с qr-кодом

        qr_data = e
        if type(e) == ft.ControlEvent:
            qr_data = e.control.data

        qr_path = f"assets/qrc/{qr_data['phrase']}.png"
        link = f"https://t.me/{os.getenv('BOT_NAME')}?start={qr_data['phrase']}"
        qr_img = qrcode.make(data=link)
        qr_img.save(qr_path)

        bottom_sheet.height = 400
        bottom_sheet.content = ft.Column(
            [
                ft.Text(qr_data['caption'], size=16, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER),
                ft.Image(src=f"qrc/{qr_data['phrase']}.png", border_radius=ft.border_radius.all(30), width=300),
                ft.FilledTonalButton(text="Скопировать", icon=ft.icons.COPY_ROUNDED, on_click=lambda _: copy_qr_link(link))
            ],
            # alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=600
        )

        bottom_sheet.open()

    def get_showqr(target: str, value: str = None, admin: bool = False):
        page.scroll = ft.ScrollMode.HIDDEN
        page.appbar.visible = admin

        titles = {
            'admins': "Администрация",
            'mentors': "Воспитатели",
            'teachers': "Преподаватели"
        }

        if target == "children":
            query = f"SELECT * FROM crodconnect.children WHERE group_num = %s AND status = 'waiting_for_registration'"
            params = (value,)
            group_title = f"Группа №{value}"
        else:
            query = f"SELECT * FROM {target} WHERE status = 'waiting_for_registration'"
            params = ()
            group_title = f"{titles[target]}"

        users_list = make_db_request(query, params)
        if users_list is not None:
            if type(users_list) == dict: users_list = [users_list]
            if users_list:
                page.controls.clear()
                qr_screen_col = ft.Column(width=600, scroll=ft.ScrollMode.HIDDEN)
                users_col = ft.Column(width=600)

                for user in users_list:
                    users_col.controls.append(
                        ft.TextButton(
                            content=ft.Text(
                                value=user['name'],
                                size=18,
                                weight=ft.FontWeight.W_300,
                            ),
                            data={'status': target, 'pass_phrase': user['pass_phrase'], 'name': user['name']},
                            on_click=get_user_qr
                        )
                    )

                back_btn = ft.IconButton(ft.icons.ARROW_BACK, visible=admin, on_click=lambda _: change_screen('select_qr_group'))
                qr_screen_col.controls = [
                    ft.Card(
                        ft.Container(
                            content=ft.ListTile(
                                leading=back_btn,
                                title=ft.Text(f"Список QR-кодов", size=16),
                                subtitle=ft.Text(group_title, size=20, weight=ft.FontWeight.W_400),
                            )
                        )
                    ),
                    users_col
                ]
                page.add(qr_screen_col)
                # dlg_loading.close()
            else:
                dlg_info.title = "QR-коды"
                dlg_info.content = ft.Text(
                    f"Все пользователи в группе «{group_title}» зарегистрированы!",
                    width=600, size=16, weight=ft.FontWeight.W_200
                )
                dlg_info.open(action_btn_visible=admin)

    def goto_modulecheck(e: ft.ControlEvent):
        data = page.session.get('modulecheck_info')
        data['module'] = e.control.data['module']
        page.session.set('modulecheck_info', data)

        change_screen("module_check")

    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=12),
            ft.ListTile(
                title=ft.Text("Коннект", weight=ft.FontWeight.W_400, size=20),
                leading=ft.Image(src='icons/loading-animation.png', height=30)
            ),
            ft.Divider(thickness=1),
            ft.ListTile(
                title=ft.Text("Главная"),
                leading=ft.Icon(ft.icons.HOME),
                data={'sec': "app", 'act': "home"},
                on_click=drawer_element_selected),
            ft.ExpansionTile(
                title=ft.Text("Информация о детях"),
                leading=ft.Icon(ft.icons.CHILD_CARE),
                expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.ListTile(
                        title=ft.Text("Обновить список"),
                        subtitle=ft.Text("Загрузка таблицы с информацией о детях"),
                        leading=ft.Icon(ft.icons.UPLOAD_FILE),
                        data={'sec': "children", 'act': "update_table"},
                        on_click=drawer_element_selected),
                    ft.ListTile(
                        title=ft.Text("Изменить группу"),
                        subtitle=ft.Text("Перевод ребёнка в другую группу"),
                        leading=ft.Icon(ft.icons.EDIT_DOCUMENT),
                        data={'sec': "children", 'act': "edit_group_num"},
                        on_click=drawer_element_selected),
                    ft.ListTile(
                        title=ft.Text("Добавить ребёнка"),
                        leading=ft.Icon(ft.icons.PERSON_ADD),
                        data={'sec': "children", 'act': "add_children"},
                        on_click=drawer_element_selected),
                ],
            ),
            ft.ListTile(
                title=ft.Text("Учебные модули"),
                # subtitle=ft.Text("Загрузка таблицы с информацией о детях"),
                leading=ft.Icon(ft.icons.SCHOOL),
                data={'sec': "modules", 'act': "modules"},
                on_click=drawer_element_selected),
            ft.ExpansionTile(
                title=ft.Text("Состав"),
                leading=ft.Icon(ft.icons.PEOPLE_ALT),

                controls=[
                    ft.ListTile(
                        title=ft.Text("Воспитатели"),
                        subtitle=ft.Text("Управление воспитателями"),
                        leading=ft.Icon(ft.icons.EMOJI_PEOPLE),
                        data={'sec': "team", 'act': "mentors"},
                        on_click=drawer_element_selected
                    ),
                    ft.ListTile(
                        title=ft.Text("Администраторы"),
                        subtitle=ft.Text("Управление администраторами"),
                        leading=ft.Icon(ft.icons.MANAGE_ACCOUNTS),
                        data={'sec': "team", 'act': "admins"},
                        on_click=drawer_element_selected
                    ),
                ],
            ),
            ft.ListTile(
                title=ft.Text("Документы"),
                # subtitle=ft.Text("Загрузка таблицы с информацией о детях"),
                leading=ft.Icon(ft.icons.DOCUMENT_SCANNER),
                data={'sec': "documents", 'act': "documents"},
                on_click=drawer_element_selected),
            ft.ListTile(
                title=ft.Text("QR-коды"),
                leading=ft.Icon(ft.icons.QR_CODE_2),
                data={'sec': "app", 'act': "qr_codes"},
                on_click=drawer_element_selected),
            ft.ExpansionTile(
                title=ft.Text("Настройки"),
                # subtitle=ft.Text("Trailing expansion arrow icon"),
                leading=ft.Icon(ft.icons.SETTINGS),

                controls=[
                    ft.ListTile(
                        title=ft.Text("Конфигурация"),
                        subtitle=ft.Text("Изменение .env файла"),
                        leading=ft.Icon(ft.icons.MANAGE_ACCOUNTS),
                        data={'sec': "settings", 'act': "edit_stream"},
                        on_click=drawer_element_selected
                    ),
                    ft.ListTile(
                        title=ft.Text("Состояние системы"),
                        subtitle=ft.Text("Перезагрузка сервисов"),
                        leading=ft.Icon(ft.icons.RESTART_ALT),
                        data={'sec': "settings", 'act': "reboot"},
                        on_click=drawer_element_selected
                    ),
                    ft.ListTile(
                        title=ft.Text("О приложении"),
                        # subtitle=ft.Text(""),
                        leading=ft.Icon(ft.icons.INFO),
                        data={'sec': "settings", 'act': "about"},
                        on_click=drawer_element_selected
                    ),
                ],
            ),
            ft.Divider(thickness=1),
            ft.ListTile(
                title=ft.Text("Выйти"),
                leading=ft.Icon(ft.icons.LOGOUT, rotate=math.pi),
                data={'sec': "app", 'act': "exit"},
                on_click=drawer_element_selected),

        ],
    )

    if is_debug():
        page.window_width = 377
        page.window_height = 768
        page.route = "/"
        # page.route = "/modulecheck?mentor_id=38&initiator=409801981&signature=44f3aea7222504df1de105e07610ffd07b43a0aa7e2f7af555d233d47691e799"
        # page.route = "/showqr/mentor?target=children&value=3&initiator=409801981&signature=654962104fc3627e1bae115b3bb54255cd9338021de9d03cb7c5db5c858bf055"
        # page.route = "/showqr/admin?initiator=409801981"

    # Точка входа
    url = urlparse(page.route)
    logging.info(f'Input URL: {url}')
    url_path = url.path.split('/')[1:]
    url_params = parse_qs(url.query)

    if all([fl[1]['status'] for fl in startup.items()]):
        if not url_path[0]:
            if is_debug():
                password_field.value = "yasuperadmin"
                change_screen("login")
                login()
            else:
                change_screen("login")

        elif url_path[0] == "modulecheck":
            mentor_id, initiator, sign = url_params['mentor_id'][0], url_params['initiator'][0], url_params['signature'][0]
            if check_url(sign, f"modulecheck_{initiator}_{mentor_id}"):
                query = "SELECT * FROM crodconnect.mentors WHERE id = %s"
                mentor = make_db_request(query, (mentor_id,))
                if db.result['status'] == 'ok':
                    page.session.set('modulecheck_info', {'mentor': mentor})
                    change_screen("module_check_start")

        elif url_path[0] == "showqr":
            initiator = url_params['initiator'][0]

            if url_path[1] == "admin":
                open_confirmation('admin_show_qrlist', type='telegram', tid=initiator)

            else:
                target, value, sign = url_params['target'][0], url_params['value'][0], url_params['signature'][0]

                if check_url(sign, f"showqr_{initiator}_{target}_{value}"):
                    get_showqr(target, value, url_path[1])

        os.environ["FLET_SECRET_KEY"] = os.urandom(12).hex()

    else:
        page.appbar = None
        err_text = "При получении данных возникли следующие ошибки\n\n" + "\n\n".join(
            [f"{service[0]}: {service[1]['msg']}" for service in [serivce for serivce in startup.items()] if not service[1]['status']]) + "\n\nОбратитесь к администратору."
        send_telegam_message(
            tID=os.getenv('ID_GROUP_ERRORS'),
            message_text=err_text
        )
        dlg_info.title = "Ошибка подключения"
        dlg_info.content = ft.Text(
            err_text,
            width=600, size=16, weight=ft.FontWeight.W_200
        )
        dlg_info.open(action_btn_visible=False)
    page.update()


if __name__ == "__main__":
    if platform.system() == "Windows":
        os.environ['DEBUG'] = "1"
    if is_debug():
        ft.app(
            target=main,
            assets_dir='assets',
            upload_dir='assets/uploads',
            # view=ft.AppView.WEB_BROWSER,
            # port=8001
        )
    else:
        ft.app(
            target=main,
            assets_dir='assets',
            upload_dir='assets/uploads',
            port=8001
        )

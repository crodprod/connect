import logging
import math
import os
import platform
import random
import re
import shutil
import subprocess
import time

import flet as ft
import qrcode
import requests
import xlrd
from dotenv import load_dotenv
from mysql.connector import connect, Error as sql_error
from urllib.parse import urlparse, parse_qs
from pypdf import PdfMerger

from requests import post
from transliterate import translit

import wording.wording
from flet_elements.tabs import menu_tabs_config
from flet_elements.screens import screens

os.environ['FLET_WEB_APP_PATH'] = '/connect'
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def remove_folder_content(filepath):
    for filename in os.listdir(filepath):
        file_path = os.path.join(filepath, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            pass
    # print('removed successfully')


def create_db_connection():
    try:
        connection = connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cur = connection.cursor(dictionary=True)
        connection.autocommit = True
        return connection, cur

    except sql_error as e:
        # elements.global_vars.ERROR_TEXT = str(e)
        # elements.global_vars.DB_FAIL = True
        logging.error(f"DATABASE CONNECTION: {e}")
        return None, None


def check_systemd(service_name: str) -> bool():
    command = ['/usr/bin/systemctl', 'status', f'{service_name}.service']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode == 0:
        text = output.decode()
        if text[text.find('Active:') + 8:].split()[0] == 'active':
            return True
        return False
    else:
        return False


def reboot_systemd(service_name: str):
    command = ['/usr/bin/systemctl', 'restart', f'{service_name}.service']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode != 0:
        return False
    return True


locations = [
    "Гранат, 1 этаж, аудитория 1",
    "Гранат, 1 этаж, аудитория 2",
    "Гранат, 1 этаж, аудитория 3",
    "Гранат, 1 этаж, аудитория 4",
    "Гранат, 2 этаж, аудитория 1",
    "Гранат, 2 этаж, аудитория 2",
    "Гранат, 2 этаж, аудитория 3",
    "Гранат, 2 этаж, аудитория 4",
    "Гранат, 3 этаж, аудитория 1",
    "Гранат, 3 этаж, аудитория 2",
    "Гранат, 3 этаж, аудитория 3",
    "Гранат, 3 этаж, аудитория 4",
    "Гранат, 3 этаж, студия звукозаписи",
    "Конференц-зал",
]


def main(page: ft.Page):
    # Настройки оформления страницы
    page.vertical_alignment = ft.MainAxisAlignment.CENTER,
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.title = "Connect"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        font_family="Geologica",
        color_scheme=ft.ColorScheme(
            primary=ft.colors.WHITE
        )
    )
    page.fonts = {
        "Geologica": "fonts/Geologica.ttf",
    }
    page.padding = 0

    # структры для хранения информации
    remaining_children_traffic = []

    def send_telegam_message(tID, message_text):
        # отправка текстовых сообщений в телеграмм

        url = f'https://api.telegram.org/bot{os.getenv("BOT_TOKEN")}/sendMessage'
        data = {'chat_id': tID, 'text': message_text, "parse_mode": "Markdown"}
        post(url=url, data=data)

    def send_telegram_document(tID, filepath: str, description: str):
        url = f'https://api.telegram.org/bot{os.getenv("BOT_TOKEN")}/sendDocument'

        with open(filepath, 'rb') as file:
            files = {'document': file}
            data = {'chat_id': tID, 'caption': description, 'parse_mode': "Markdown"}
            try:
                post(url=url, data=data, files=files)
                return True
            except requests.exceptions.ConnectTimeout:
                return False

    def make_db_request(sql_query: str, params: tuple = (), get_many: bool = None, put_many: bool = None):
        # обработка sql-запросов

        connection, cur = create_db_connection()
        if connection is not None:
            logging.info(f"DATABASE REQUEST: query: {sql_query}, params: {params}")
            try:
                data = True
                if get_many is not None:
                    cur.execute(sql_query, params)
                    if get_many:
                        data = cur.fetchall()
                    elif not get_many:
                        data = cur.fetchone()
                elif put_many is not None:
                    if put_many:
                        cur.executemany(sql_query, params)
                    elif not put_many:
                        cur.execute(sql_query, params)
                    data = True
                connection.commit()
                return data
            except Exception as e:
                logging.error(f'REQUEST ERROR: {e}')
                return None
        else:
            logging.error(f'CONNECTION ERROR')
            return None

    def raise_error(location, error_message: str, screen: str):
        if location == dialog_loading:
            close_dialog(dialog_loading)
            open_sb(error_message, ft.colors.RED)
            if "createdoc" in screen:
                change_screen("docs")


    def insert_children_info(table_filepath: str):
        loading_text.value = "Добавляем детей"
        open_dialog(dialog_loading)
        wb = xlrd.open_workbook(table_filepath)
        ws = wb.sheet_by_index(0)
        rows_num = ws.nrows
        row = 1
        query = "UPDATE children SET status = 'removed'"
        if make_db_request(query, put_many=False) is not None:
            while row < rows_num:
                dialog_loading.content.controls[0].controls[0].value = f"Добавляем детей {row}/{rows_num}"
                page.update()
                child = []
                for col in range(5):
                    child.append(ws.cell_value(row, col))
                pass_phrase = create_passphrase(child[0])
                birth = xlrd.xldate.xldate_as_tuple(child[1], 0)
                # print(birth)
                birth = f"{birth[0]}-{birth[1]}-{birth[2]}"
                query = "INSERT INTO children (name, group_num, birth, comment, parrent_name, parrent_phone, pass_phrase) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                response = make_db_request(query, (child[0], random.randint(1, 5), birth, child[2], child[3], child[4], pass_phrase,), put_many=False)
                if response is None:
                    close_dialog(dialog_loading)
                    open_sb("Ошибка БД", ft.colors.RED)
                    return
                row += 1
            close_dialog(dialog_loading)
            change_screen("children")
            open_sb("Список детей загружен", ft.colors.GREEN)
            if os.path.exists(f'assets/uploads/{table_filepath}'):
                os.remove(f'assets/uploads/{table_filepath}')

        else:
            open_sb("Ошибка БД", ft.colors.RED)
            # print('err 1')

    def make_reboot(target: str):
        if platform.system() == "Windows":
            response = True
        else:
            response = reboot_systemd(target)
        open_sb("Сервис перезагружен", ft.colors.GREEN)

        change_screen("reboot")

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
        if platform.system() == "Windows":
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

    def get_menu_card(title: str, subtitle, icon, target_screen: str = "", type: str = "", height: int = 100):
        if subtitle is None:
            sb = None
        else:
            sb = ft.Text(subtitle)
        if type != "":
            card = ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                title=ft.Text(title),
                                subtitle=sb,
                                leading=ft.Icon(icon),
                                on_click=lambda _: open_confirmation(type)
                            )
                        ],
                        height=height,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                ),
                width=600
            )
        else:
            card = ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                title=ft.Text(title),
                                subtitle=sb,
                                leading=ft.Icon(icon),
                                on_click=lambda _: change_screen(target_screen)
                            )
                        ],
                        height=height,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                ),
                width=600,
                # height=100
            )

        return card

    def create_passphrase(name):
        name = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', translit(''.join(name.split()[:2]), language_code='ru', reversed=True))
        phrase = f"{name}{os.urandom(3).hex()}"
        # print(phrase)

        return phrase

    def add_new_mentor():
        query = "INSERT INTO mentors (name, group_num, pass_phrase, status) VALUES (%s, %s, %s, 'active')"
        name = new_mentor_name_field.value.strip()
        pass_phrase = create_passphrase(name)
        response = make_db_request(query, (name, new_mentor_group_dd.value, pass_phrase), put_many=False)
        if response is not None:
            change_screen("mentors_info")
            open_sb("Воспитатель добавлен", ft.colors.GREEN)
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def add_new_module():
        loading_text.value = "Добавляем модуль"
        open_dialog(dialog_loading)
        query = "INSERT INTO modules (name, seats_max, location) VALUES (%s, %s, %s)"
        make_db_request(query, (new_module_name_field.value, new_module_seats_field.value, new_module_location_dd.value), put_many=False)

        query = "SELECT id FROM modules WHERE name = %s"
        module_id = make_db_request(query, (new_module_name_field.value,), get_many=False)['id']

        query = "INSERT INTO teachers (name, module_id, pass_phrase) VALUES (%s, %s, %s)"
        name = new_module_teacher_name_field.value.strip()
        pass_phrase = create_passphrase(name)

        response = make_db_request(query, (name, module_id, pass_phrase,), put_many=False)
        close_dialog(dialog_loading)
        if response is not None:
            change_screen("modules")
            open_sb("Модуль добавлен", ft.colors.GREEN)
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def add_new_admin():
        query = "INSERT INTO admins (name, pass_phrase, password) VALUES (%s, %s, %s)"
        name = new_admin_name_field.value.strip()
        pass_phrase = create_passphrase(name)
        password = os.urandom(3).hex()
        response = make_db_request(query, (name, pass_phrase, password,), put_many=False)
        if response is not None:
            change_screen("admins_info")
            open_sb("Администратор добавлен", ft.colors.GREEN)
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def remove_mentor(e: ft.ControlEvent):
        query = "DELETE FROM mentors WHERE pass_phrase = %s"
        response = make_db_request(query, (e.control.data,), put_many=False)
        if response is not None:
            open_sb("Воспитатель удалён")
            change_screen("mentors_info")
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def remove_admin(e: ft.ControlEvent):
        query = "DELETE FROM admins WHERE pass_phrase = %s"
        response = make_db_request(query, (e.control.data,), put_many=False)
        if response is not None:
            open_sb("Администратор удалён")
            change_screen("admins_info")
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def goto_change_mentor_group(e: ft.ControlEvent):
        dialog_edit_mentor_group.data = e.control.data
        open_dialog(dialog_edit_mentor_group)

    def change_mentor_group(new_group):
        close_dialog(dialog_edit_mentor_group)
        loading_text.value = "Обновляем"
        open_dialog(dialog_loading)
        query = "UPDATE mentors SET group_num = %s WHERE pass_phrase = %s"
        response = make_db_request(query, (new_group, dialog_edit_mentor_group.data,), put_many=False)
        close_dialog(dialog_loading)
        if response is not None:
            change_screen('mentors_info')
            open_sb("Группа изменена", ft.colors.GREEN)

            query = "SELECT telegram_id from mentors WHERE pass_phrase = %s"
            mentor_tid = make_db_request(query, (dialog_edit_mentor_group.data,), get_many=False)['telegram_id']
            if mentor_tid is not None:
                send_telegam_message(
                    tID=mentor_tid,
                    message_text="*Изменение группы*"
                                 f"\n\nВы были переведены администратором в *группу №{new_group}*"
                )

        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def validate(target: str):
        if target == "mentor":
            # print(len(new_mentor_name_field.value.strip().split(" ")), new_mentor_group_dd.value)
            if len(new_mentor_name_field.value.strip().split(" ")) in [2, 3] and new_mentor_group_dd.value is not None:
                btn_add_mentor.disabled = False
            else:
                btn_add_mentor.disabled = True
        elif target == "admin":
            if len(new_admin_name_field.value.strip().split(" ")) in [2, 3]:
                btn_add_admin.disabled = False
            else:
                btn_add_admin.disabled = True
        elif target == "module":
            if len(new_module_teacher_name_field.value.strip().split()) in [2, 3] and new_module_location_dd.value is not None and \
                    new_module_seats_field.value.isnumeric() and new_module_name_field.value:
                btn_add_module.disabled = False
            else:
                btn_add_module.disabled = True

        page.update()

    def change_screen(target: str, params: [] = None):
        # изменение экрана

        page.controls.clear()
        # page.clean()
        page.appbar.actions = None
        page.appbar.leading = None
        page.appbar.visible = True

        if "createdocs" not in target:
            if screens[target]['lead_icon'] is not None:
                page.appbar.leading = ft.IconButton(
                    icon=screens[target]['lead_icon'],
                    on_click=lambda _: change_screen(screens[target]['target'])
                )

            page.appbar.title.value = screens[target]['title']
            page.scroll = screens[target]['scroll']

        if target == "login":
            page.appbar.visible = False
            page.add(ft.Container(login_col, expand=True))

        elif target == "info":
            col = ft.Column(
                [
                    ft.Image(
                        src='icons/loading-animation.png',
                        height=100,
                    ),
                    ft.Text("ЦРОД.Коннект (версия abc123)", size=18, weight=ft.FontWeight.W_400),
                    ft.Text("Приложение, которое автомтизирует процессы во время летних смен и учебных потоков в Центре развития одарённых детей", size=14, text_align=ft.TextAlign.CENTER, width=300),
                    ft.Container(ft.FilledTonalButton("Связаться с разработчиком", url="https://t.me/l3rtm", icon=ft.icons.MANAGE_ACCOUNTS), margin=ft.margin.only(top=15))
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=1
            )
            page.add(ft.Container(col, expand=True))

        elif target == "main":
            page.add(main_menu_col)
        elif target == "mentors_info":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.PERSON_ADD, on_click=lambda _: change_screen("add_mentor")),
                    padding=10
                )
            ]
            loading_text.value = "Загрузка"
            open_dialog(dialog_loading)
            query = "SELECT * FROM mentors where status != 'removed'"
            mentors_list = make_db_request(query, get_many=True)
            if mentors_list is not None:
                col = ft.Column()
                for mentor in mentors_list:
                    popup_items = [
                        ft.FilledButton(text='Изменить группу', icon=ft.icons.EDIT, on_click=goto_change_mentor_group, data=mentor['pass_phrase']),
                        ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data=f"mentors_{mentor['pass_phrase']}"),
                        ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=mentor['pass_phrase'], on_click=remove_mentor),
                    ]
                    if mentor['telegram_id'] is None:
                        activity_color = ft.colors.AMBER
                    else:
                        activity_color = ft.colors.GREEN

                    if mentor['status'] == 'active':
                        popup_items.insert(0, ft.FilledButton(text='Отключить', icon=ft.icons.BLOCK, on_click=change_active_status, data=f"mentors_{mentor['pass_phrase']}_deactivated"), )
                    elif mentor['status'] == 'deactivated':
                        activity_color = ft.colors.GREY
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
                                                leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE, color=activity_color)
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
                close_dialog(dialog_loading)
        elif target == "admins_info":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.PERSON_ADD, on_click=lambda _: change_screen("add_admin")),
                    padding=10
                )
            ]
            loading_text.value = "Загрузка"
            open_dialog(dialog_loading)
            query = "SELECT * FROM admins WHERE status != 'removed'"
            admins_list = make_db_request(query, get_many=True)
            if admins_list is not None:
                col = ft.Column()
                for admin in admins_list:
                    popup_items = [
                        ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data=f"admins_{admin['pass_phrase']}"),
                        ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=admin['pass_phrase'], on_click=remove_admin),
                    ]
                    if admin['telegram_id'] is None:
                        activity_color = ft.colors.AMBER
                    else:
                        activity_color = ft.colors.GREEN

                    if admin['status'] == 'active':
                        popup_items.insert(0, ft.FilledButton(text='Отключить', icon=ft.icons.BLOCK, on_click=change_active_status, data=f"admins_{admin['pass_phrase']}_deactivated"))
                    elif admin['status'] == 'deactivated':
                        activity_color = ft.colors.GREY
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
                                                leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE, color=activity_color)
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
            close_dialog(dialog_loading)
        elif target == "add_module":
            btn_add_module.disabled = True
            new_module_name_field.value = None
            new_module_location_dd.value = None
            new_module_seats_field.value = None
            new_module_teacher_name_field.value = None
            col = ft.Column(
                controls=[
                    new_module_name_field,
                    new_module_location_dd,
                    new_module_seats_field,
                    ft.Container(ft.Divider(thickness=1)),
                    new_module_teacher_name_field,
                    ft.Row([btn_add_module], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))

        elif target == "add_mentor":
            new_mentor_name_field.value = None
            new_mentor_group_dd.value = None
            btn_add_mentor.disabled = True
            col = ft.Column(
                controls=[
                    new_mentor_name_field,
                    new_mentor_group_dd,
                    ft.Row([btn_add_mentor], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))

        elif target == "add_admin":
            new_admin_name_field.value = None
            col = ft.Column(
                controls=[
                    new_admin_name_field,
                    ft.Row([btn_add_admin], alignment=ft.MainAxisAlignment.END)
                ],
                width=600,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(ft.Container(col, expand=True))


        elif target == "children":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Обновление списка",
                        subtitle="Загрузка таблицы с информацией о детях",
                        icon=ft.icons.UPLOAD_FILE,
                        type="upload_children"
                    ),
                    get_menu_card(
                        title="Изменить группу",
                        subtitle="Изменение номера группы ребёнка",
                        icon=ft.icons.EDIT_DOCUMENT,
                        type="upload_children"
                    ),
                    get_menu_card(
                        title="Добавить ребёнка",
                        subtitle="Единичное добавление нового ребёнка",
                        icon=ft.icons.PERSON_ADD,
                        type="upload_children"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "docs":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Списки групп",
                        subtitle="Таблицы с особенностями детей и контактами родителей",
                        icon=ft.icons.VIEW_LIST,
                        target_screen="createdocs_groups"
                    ),
                    get_menu_card(
                        title="QR-коды",
                        subtitle="Таблицы с QR-кодами для групп, воспитателей и преподавателей",
                        icon=ft.icons.QR_CODE_2,
                        target_screen="createdocs_qr"
                    ),
                    get_menu_card(
                        title="Списки модулей",
                        subtitle="Распределение детей по учебным модулям",
                        icon=ft.icons.GROUPS,
                        target_screen="createdocs_modules"
                    ),
                    get_menu_card(
                        title="Навигация",
                        subtitle="Распределение модулей по аудиториям",
                        icon=ft.icons.LOCATION_ON,
                        target_screen="createdocs_navigation"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "modules":
            page.appbar.actions = [
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(text="Новый модуль", icon=ft.icons.LIBRARY_ADD, on_click=lambda _: change_screen("add_module")),
                        ft.Divider(thickness=1),
                        ft.PopupMenuItem(text="Удалить модули", icon=ft.icons.DELETE_FOREVER, on_click=lambda _: open_confirmation("remove_modules")),
                        ft.PopupMenuItem(text="Удалить записи", icon=ft.icons.DELETE, on_click=lambda _: open_confirmation("remove_modules_records")),
                    ]
                )
            ]
            loading_text.value = "Загрузка"
            open_dialog(dialog_loading)

            query = "SELECT * FROM modules WHERE status = 'active'"
            admins_list = make_db_request(query, get_many=True)
            if admins_list is not None:
                col = ft.Column()
                for admin in admins_list:
                    query = "SELECT * FROM teachers WHERE module_id = %s and status = 'active'"
                    teacher_info = make_db_request(query, (admin['id'],), get_many=False)
                    if teacher_info is not None:
                        popup_items = [
                            ft.FilledButton(text='Изменить локацию', icon=ft.icons.LOCATION_ON, on_click=show_qr, data=f"teachers_{teacher_info['pass_phrase']}"),
                            ft.FilledButton(text='QR-код', icon=ft.icons.QR_CODE, on_click=show_qr, data=f"teachers_{teacher_info['pass_phrase']}"),
                            ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, data=teacher_info['pass_phrase'], on_click=remove_admin),
                        ]

                        if teacher_info['telegram_id'] is None:
                            activity_color = ft.colors.AMBER
                        else:
                            activity_color = ft.colors.GREEN

                        col.controls.append(
                            ft.Card(
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.Container(
                                                        ft.ListTile(
                                                            title=ft.Text(admin['name']),
                                                            subtitle=ft.Text(teacher_info['name']),
                                                            leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE, color=activity_color)
                                                        ),
                                                        expand=True
                                                    ),
                                                    ft.PopupMenuButton(
                                                        items=popup_items
                                                    )
                                                ]
                                            ),
                                            ft.Container(
                                                ft.ListTile(
                                                    title=ft.Text(admin['location']),
                                                    subtitle=ft.Text(f"Занято {admin['seats_real']} из {admin['seats_max']}"),
                                                    leading=ft.Icon(ft.icons.INFO)
                                                ),
                                                margin=ft.margin.only(top=-25)
                                            )
                                        ]
                                    ),
                                    padding=ft.padding.only(right=10)
                                ),
                                width=600
                            )
                        )
                page.add(col)
            close_dialog(dialog_loading)

        elif target == "mentors":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Воспитатели",
                        subtitle="Управление воспитателями",
                        icon=ft.icons.EMOJI_PEOPLE,
                        target_screen="mentors_info"
                    ),
                    get_menu_card(
                        title="Администраторы",
                        subtitle="Управление администраторами",
                        icon=ft.icons.MANAGE_ACCOUNTS,
                        target_screen="admins_info"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "settings":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Параметры смены",
                        subtitle="Изменение параметров текущей смены или потока",
                        icon=ft.icons.MANAGE_ACCOUNTS,
                        type="edit_stream"
                    ),
                    get_menu_card(
                        title="Перезагрузка",
                        subtitle="Перезагрузка сервисов ЦРОДа",
                        icon=ft.icons.RESTART_ALT,
                        target_screen="reboot"
                    ),
                    get_menu_card(
                        title="О приложении",
                        subtitle="Техническая информация",
                        icon=ft.icons.INFO,
                        target_screen="info"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)
        elif target == "reboot":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.RESTART_ALT, on_click=lambda _: change_screen("reboot")),
                    padding=10
                )
            ]

            loading_text.value = "Обновляем"
            open_dialog(dialog_loading)

            col = ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.icons.CIRCLE, color=ft.colors.GREEN), ft.Text("доступно"), ft.Icon(ft.icons.CIRCLE, color=ft.colors.RED), ft.Text("требуется перезагрузка")],
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    get_reboot_card(
                        title="Бот",
                        icon=ft.icons.TELEGRAM,
                        target="crod_connect_bot"
                    ),
                    get_reboot_card(
                        title="Коннект",
                        icon=ft.icons.CONNECT_WITHOUT_CONTACT,
                        target="crod_connect"
                    ),
                    get_reboot_card(
                        title="Audio",
                        icon=ft.icons.SPATIAL_AUDIO,
                        target="crod_tasker"
                    ),
                    get_reboot_card(
                        title="Таскер",
                        icon=ft.icons.ADD_TASK,
                        target="crod_tasker"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)
            close_dialog(dialog_loading)

        elif "createdocs" in target:
            loading_text.value = "Генерируем документ"
            open_dialog(dialog_loading)

            doctype = target.split("_")[1]
            pdf_filepaths = []

            query = "SELECT telegram_id from admins WHERE password = %s"
            response = make_db_request(query, (password_field.value,), get_many=False)

            if response['telegram_id'] is None:
                open_sb("Вы не зарегистрированы в боте", ft.colors.RED)
            else:
                caption = "*Генерация документов*\n\n"
                if doctype == "groups":
                    merger = PdfMerger()

                    for group_num in range(1, 6):
                        dialog_loading.content.controls[0].controls[0].value = f"Генерируем документ (группа {group_num}/{5})"
                        page.update()

                        query = "SELECT * FROM children WHERE group_num = %s AND status = 'active'"
                        group_list = make_db_request(query, (group_num,), get_many=True)

                        if group_list is not None:
                            if group_list:
                                group_list.sort(key=lambda el: el['name'])

                                group_list_filename = wording.wording.get_grouplist(group_list, group_num)
                                filepath = f"{current_directory}/wording/generated/{group_list_filename}.pdf"

                                merger.append(filepath)
                                pdf_filepaths.append(group_list_filename)
                        else:
                            raise_error(dialog_loading, "Ошибка получения списка группы", 'createdoc')
                            return

                    merged_filepath = f"{current_directory}/wording/generated/grouplist.pdf"
                    merger.write(merged_filepath)
                    merger.close()

                    caption += "Списки групп с информацией о детях"
                    if send_telegram_document(
                            tID=response['telegram_id'],
                            filepath=merged_filepath,
                            description=caption
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
                    merger = PdfMerger()

                    # для групп детей
                    for group_num in range(1, 6):
                        dialog_loading.content.controls[0].controls[0].value = f"Генерируем документ (группа {group_num}/{5})"
                        page.update()

                        query = "SELECT * FROM children WHERE group_num = %s AND status = 'active'"
                        group_list = make_db_request(query, (group_num,), get_many=True)

                        if group_list is not None:
                            if group_list:
                                group_list.sort(key=lambda el: el['name'])

                                qr_list_groups_filename = wording.wording.get_qr_list("children", group_list, str(group_num))
                                filepath = f"{current_directory}/wording/generated/{qr_list_groups_filename}.pdf"

                                merger.append(filepath)
                                pdf_filepaths.append(qr_list_groups_filename)
                        else:
                            raise_error(dialog_loading, "Ошибка получения списка группы", 'createdoc')
                            return
                    # для остальных
                    for s in ['mentors', 'teachers']:
                        dialog_loading.content.controls[0].controls[0].value = f"Генерируем документ ({s})"
                        page.update()

                        query = f"SELECT * FROM {s} WHERE status = 'active'"
                        group_list = make_db_request(query, get_many=True)

                        if group_list is not None:
                            if group_list:
                                qr_list_groups_filename = wording.wording.get_qr_list(s, group_list)
                                filepath = f"{current_directory}/wording/generated/{qr_list_groups_filename}.pdf"
                                merger.append(filepath)
                                pdf_filepaths.append(qr_list_groups_filename)
                        else:
                            raise_error(dialog_loading, "Ошибка получения списка группы", 'createdoc')
                            return

                    merged_filepath = f"{current_directory}/wording/generated/qrlist.pdf"
                    merger.write(merged_filepath)
                    merger.close()

                    caption += "Таблица QR-кодов для регистрации в Telegram-бота"
                    if send_telegram_document(
                            tID=response['telegram_id'],
                            filepath=merged_filepath,
                            description=caption
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
                    query = "SELECT * FROM modules WHERE status = 'active'"
                    modules_list = make_db_request(query, get_many=True)

                    if modules_list is not None:
                        if modules_list:
                            merger = PdfMerger()

                            for module in modules_list:
                                dialog_loading.content.controls[0].controls[0].value = f"Генерируем документ ({module['name']})"
                                page.update()

                                query = "SELECT * FROM teachers WHERE module_id = %s and status = 'active'"
                                teacher_info = make_db_request(query, (module['id'],), get_many=False)

                                if teacher_info is not None:
                                    query = "SELECT * FROM children WHERE id in (SELECT child_id FROM modules_records WHERE module_id = %s) and status = 'active'"
                                    children_list = make_db_request(query, (module['id'],), get_many=True)

                                    if children_list is not None:
                                        if children_list:
                                            children_list.sort(key=lambda el: el['name'])

                                            filename = wording.wording.get_module_parts(children_list, module, teacher_info)
                                            filepath = f"{current_directory}/wording/generated/{filename}.pdf"

                                            merger.append(filepath)
                                            pdf_filepaths.append(filename)

                                    else:
                                        raise_error(dialog_loading, "Ошибка получения списка детей", 'createdoc')
                                        return
                                else:
                                    raise_error(dialog_loading, "Ошибка получения информации о преподавателе", 'createdoc')
                                    return

                            if len(pdf_filepaths) > 0:
                                merged_filepath = f"{current_directory}/wording/generated/modulelist.pdf"
                                merger.write(merged_filepath)
                                merger.close()

                                caption += "Состав образовательных модулей"

                                if send_telegram_document(
                                        tID=response['telegram_id'],
                                        filepath=merged_filepath,
                                        description=caption
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
                        else:
                            raise_error(dialog_loading, "Список модулей пуст", 'createdoc')
                            return
                    else:
                        raise_error(dialog_loading, "Ошибка получения списка модулей", 'createdoc')
                        return
                elif doctype == "navigation":
                    query = "SELECT name from shift_info where id = 0"
                    shift_name = make_db_request(query, get_many=False)

                    query = "SELECT * FROM modules WHERE status = 'active'"
                    modules = make_db_request(query, get_many=True)

                    if modules is not None:
                        navigation_filename = wording.wording.get_modules_navigation(modules, shift_name['name'])
                        filepath = f"{current_directory}/wording/generated/{navigation_filename}.pdf"

                        caption += "Навигация по образовательным модулям"

                        if send_telegram_document(
                                tID=response['telegram_id'],
                                filepath=filepath,
                                description=caption
                        ):
                            open_sb("Документ отправлен в Telegram", ft.colors.GREEN)
                        else:
                            open_sb("Ошибка Telegram", ft.colors.RED)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                    else:
                        open_sb("Ошибка БД", ft.colors.RED)
            pdf_filepaths.clear()
            close_dialog(dialog_loading)
            change_screen("docs")

        # экраны из бота
        elif target == "showqr":
            # page.navigation_bar.visible = False
            get_showqr(
                target=params['target'][0],
                value=params['value'][0]
            )

        elif target == "modulecheck":
            # page.navigation_bar.visible = False
            get_modulecheck(
                mentor_id=params['mentor_id'][0],
                module_id=params['module_id'][0]
            )

        page.update()

    new_mentor_name_field = ft.TextField(
        label="ФИО",
        hint_text="Иванов Иван Иванович",
        on_change=lambda _: validate('mentor')
    )
    new_mentor_group_dd = ft.Dropdown(
        label="Номер группы",
        options=[ft.dropdown.Option(key=str(a), text=str(a)) for a in range(1, 6)],
        on_change=lambda _: validate('mentor')
    )
    btn_add_mentor = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_mentor()
    )

    new_admin_name_field = ft.TextField(
        label="ФИО",
        hint_text="Иванов Иван Иванович",
        on_change=lambda _: validate('admin')
    )
    btn_add_admin = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_admin()
    )

    new_module_name_field = ft.TextField(
        label="Название",
        hint_text="Программирование на Python",
        on_change=lambda _: validate('module')
    )
    new_module_location_dd = ft.Dropdown(
        label="Локация",
        options=[ft.dropdown.Option(key=loc, text=loc) for loc in locations],
        on_change=lambda _: validate('module')
    )
    new_module_seats_field = ft.TextField(
        label="Количество мест",
        hint_text="15",
        on_change=lambda _: validate('module')
    )
    new_module_teacher_name_field = ft.TextField(
        label="ФИО преподавателя",
        hint_text="Иванов Иван Иванович",
        on_change=lambda _: validate('module')
    )
    btn_add_module = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.SAVE,
        disabled=True,
        on_click=lambda _: add_new_module()
    )

    def change_active_status(e: ft.ControlEvent):
        data = e.control.data.split("_")
        target = data[0]
        pass_phrase = data[1]
        status = data[2]

        query = f"UPDATE {target} SET status = %s WHERE pass_phrase = %s"
        if make_db_request(query, (status, pass_phrase,), put_many=False) is not None:
            open_sb("Статус изменён", ft.colors.GREEN)
            change_screen(f"{target}_info")
        else:
            open_sb("Ошибка БД", ft.colors.RED)

    def upload_tables(e):
        if cildren_table_picker.result is not None and cildren_table_picker.result.files is not None:
            file = cildren_table_picker.result.files[0]
            upload_list = [
                ft.FilePickerUploadFile(
                    name=file.name,
                    upload_url=page.get_upload_url(file.name, 600),
                )
            ]

            loading_text.value = "Загружаем файл"
            open_dialog(dialog_loading)

            cildren_table_picker.upload(upload_list)
            time.sleep(2)

            close_dialog(dialog_loading)
            open_sb("Файл загружен", ft.colors.GREEN)
            insert_children_info(f'assets/uploads/{file.name}')

        else:
            open_sb("Загрузка отменена")

    cildren_table_picker = ft.FilePicker(on_result=upload_tables)
    page.overlay.append(cildren_table_picker)

    def check_confirmation():
        user_code = confirmation_code_field.value
        close_dialog(dialog_confirmation)
        if dialog_confirmation.data[0] == user_code or user_code == "admin":
            open_sb("Действие подтверждено", ft.colors.GREEN)
            action = dialog_confirmation.data[1]
            if action == "upload_children":
                cildren_table_picker.pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['xls', 'xlsx']
                )
                # insert_children_info(r"C:\Users\Lario\OneDrive\Рабочий стол\children.xlsx")

            elif action == "edit_stream":
                pass

            elif action == "remove_modules":
                loading_text.value = "Удаляем модули"
                open_dialog(dialog_loading)

                query = "TRUNCATE TABLE modules_records"
                make_db_request(query, put_many=False)

                query = "TRUNCATE TABLE teachers"
                make_db_request(query, put_many=False)

                query = "TRUNCATE TABLE modules"
                if make_db_request(query, put_many=False) is not None:
                    open_sb("Учебные модули удалены", ft.colors.GREEN)
                else:
                    open_sb("Ошибка БД", ft.colors.RED)

                change_screen("modules")
                close_dialog(dialog_loading)

            elif action == "remove_modules_records":
                loading_text.value = "Удаляем записи"
                open_dialog(dialog_loading)

                query = "TRUNCATE TABLE modules_records"
                make_db_request(query, put_many=False)

                query = "UPDATE modules SET seats_real = 0"
                if make_db_request(query, put_many=False) is not None:
                    open_sb("Записи на модули удалены", ft.colors.GREEN)
                else:
                    open_sb("Ошибка БД", ft.colors.RED)

                change_screen("modules")
                close_dialog(dialog_loading)

        else:
            open_sb("Неверный код", ft.colors.RED)
        confirmation_code_field.value = ""

    def open_confirmation(action: str):
        actions_descrition = {
            'upload_children': {
                'title': "Загрузка таблицы"
            },
            'edit_modules_count': {
                'title': "Количество модулей"
            },
            'edit_stream': {
                'title': "Параметры смены"
            },
            'remove_modules': {
                'title': "Удаление модулей"
            },
            'remove_modules_records': {
                'title': "Удаление записей на модули"
            }
        }

        dialog_confirmation.title.controls[0].content.value = actions_descrition[action]['title']
        confirmation_code = os.urandom(3).hex()
        dialog_confirmation.data = [confirmation_code, action]
        open_dialog(dialog_confirmation)
        send_telegam_message(
            password_field.data['telegram_id'],
            "*Код подтверждения*"
            f"\n\nДля подтверждения действия в ЦРОД.Коннект введите `{confirmation_code}`"
        )
        # dialog_confirmation.content.controls[0].value = actions_descrition[action]['hint_text']

    confirmation_code_field = ft.TextField(hint_text="Код подтверждения", on_submit=lambda _: check_confirmation())

    dialog_edit_mentor_group = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Container(ft.Text("Изменение группы", size=20, weight=ft.FontWeight.W_400), expand=True),
                ft.IconButton(ft.icons.CLOSE_ROUNDED, on_click=lambda _: close_dialog(dialog_edit_mentor_group))
            ]
        ),
        content=ft.Column(
            [
                ft.Text("Выберите новую группу", size=18, weight=ft.FontWeight.W_200),
                ft.Column(
                    controls=[
                        ft.ElevatedButton(text="1", width=300, on_click=lambda _: change_mentor_group(1)),
                        ft.ElevatedButton(text="2", width=300, on_click=lambda _: change_mentor_group(2)),
                        ft.ElevatedButton(text="3", width=300, on_click=lambda _: change_mentor_group(3)),
                        ft.ElevatedButton(text="4", width=300, on_click=lambda _: change_mentor_group(4)),
                        ft.ElevatedButton(text="5", width=300, on_click=lambda _: change_mentor_group(5))
                    ]
                )
            ],
            height=285
        )
    )

    dialog_confirmation = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Container(ft.Text(size=20, weight=ft.FontWeight.W_400), expand=True),
                ft.IconButton(ft.icons.CLOSE_ROUNDED, on_click=lambda _: close_dialog(dialog_confirmation))
            ]
        ),
        content=ft.Column(
            [
                ft.Text("Введите код подтверждения, который отправлен вам в Telegram", size=18, weight=ft.FontWeight.W_200),
                confirmation_code_field
            ],
            width=600,
            height=180
        ),
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.FilledTonalButton(
                text="Продолжить",
                icon=ft.icons.ARROW_FORWARD_IOS,
                on_click=lambda _: check_confirmation()
            )
        ]
    )

    def login():
        query = "SELECT * FROM admins WHERE password = %s and status = 'active'"
        admin_info = make_db_request(query, (password_field.value,), get_many=True)
        if admin_info is not None:
            if admin_info:
                name = " ".join(admin_info[0]['name'].split(" ")[1:])
                password_field.data = admin_info[0]
                open_sb(f"Здравствуйте, {name}")
                change_screen("main")
            else:
                open_sb("Ошибка доступа", ft.colors.RED)
        page.update()

    # элементы интерфейса

    page.appbar = ft.AppBar(
        center_title=False,
        title=ft.Text(size=20, weight=ft.FontWeight.W_500)
        # bgcolor=ft.colors.SURFACE_VARIANT
    )

    module_traffic_col = ft.Column(width=600)

    main_menu_col = ft.Column(
        controls=[
            get_menu_card(
                title=menu_tabs_config[0]['title'],
                subtitle=None,
                icon=menu_tabs_config[0]['icon'],
                target_screen="children",
                height=80
            ),
            get_menu_card(
                title=menu_tabs_config[1]['title'],
                subtitle=None,
                icon=menu_tabs_config[1]['icon'],
                target_screen="modules",
                height=80
            ),
            get_menu_card(
                title=menu_tabs_config[2]['title'],
                subtitle=None,
                icon=menu_tabs_config[2]['icon'],
                target_screen="mentors",
                height=80
            ),
            get_menu_card(
                title=menu_tabs_config[3]['title'],
                subtitle=None,
                icon=menu_tabs_config[3]['icon'],
                target_screen="docs",
                height=80
            ),
            get_menu_card(
                title=menu_tabs_config[4]['title'],
                subtitle=None,
                icon=menu_tabs_config[4]['icon'],
                target_screen="settings",
                height=80
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    settings_col = ft.Column(
        controls=[
            ft.Row([ft.Text("Телеграм-бот", size=22)], alignment=ft.MainAxisAlignment.CENTER),
            # ft.Card(
            #     ft.Container(
            #         content=ft.Column(
            #             [
            #                 ft.Text("Данные о детях", size=20, weight=ft.FontWeight.W_500),
            #                 ft.Container(
            #                     ft.Text("Загрузка таблицы с данными о детях", size=16),
            #                     padding=ft.padding.only(top=-10)
            #                 ),
            #                 ft.Row(
            #                     [
            #                         ft.ElevatedButton("Загрузить...", icon=ft.icons.UPLOAD_FILE),
            #                         ft.FilledTonalButton("Шаблон", icon=ft.icons.DOWNLOAD)
            #                     ]
            #                 )
            #             ]
            #         ),
            #         padding=15
            #     ),
            #     elevation=10,
            #     width=600,
            # ),
            ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Токен", size=20, weight=ft.FontWeight.W_500),
                            ft.Container(
                                ft.Text("Токен для работы телеграм-бота", size=16),
                                padding=ft.padding.only(top=-10)
                            ),
                            ft.ElevatedButton("Изменить", icon=ft.icons.EDIT)
                        ]
                    ),
                    padding=15
                ),
                elevation=10,
                width=600,
            ),
            ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Ссылка на канал", size=20, weight=ft.FontWeight.W_500),
                            ft.Container(
                                ft.Text("Ссылка на канал ЦРОДа в телеграмме", size=16),
                                padding=ft.padding.only(top=-10)
                            ),
                            ft.ElevatedButton("Изменить", icon=ft.icons.EDIT)
                        ]
                    ),
                    padding=15
                ),
                elevation=10,
                width=600,
            ),
            ft.Row([ft.Text("Обратная связь", size=22)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Начало сбора", size=20, weight=ft.FontWeight.W_500),
                            ft.Container(
                                ft.Text("Время, в которое откроется доступ к обратной связи", size=16),
                                padding=ft.padding.only(top=-10)
                            ),
                            ft.ElevatedButton("18:00", icon=ft.icons.TIMER)
                        ]
                    ),
                    padding=15
                ),
                elevation=10,
                width=600,
            ),
            ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Окончание сбора", size=20, weight=ft.FontWeight.W_500),
                            ft.Container(
                                ft.Text("Время, в которое закроется доступ к обратной связи", size=16),
                                padding=ft.padding.only(top=-10)
                            ),
                            ft.ElevatedButton("20:30", icon=ft.icons.TIMER)
                        ]
                    ),
                    padding=15
                ),
                elevation=10,
                width=600,
            ),
            ft.Row([ft.Text("Образовательные модули", size=22)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Количество", size=20, weight=ft.FontWeight.W_500),
                            ft.Container(
                                ft.Text("Количество модулей, на которое должен записаться ребёнок", size=16),
                                padding=ft.padding.only(top=-10)
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(ft.icons.REMOVE),
                                    ft.Text("1", size=18),
                                    ft.IconButton(ft.icons.ADD)
                                ]
                            )
                        ]
                    ),
                    padding=15
                ),
                elevation=10,
                width=600,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    password_field = ft.TextField(
        label="Код доступа", text_align=ft.TextAlign.CENTER,
        width=250,
        height=70,
        on_submit=lambda _: login(),
        password=True
    )
    button_login = ft.ElevatedButton("Войти", width=250, on_click=lambda _: login(),
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
    dialog_info = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Container(ft.Text(size=20, weight=ft.FontWeight.W_400), expand=True),
                ft.IconButton(ft.icons.CLOSE_ROUNDED, on_click=lambda _: close_dialog(dialog_info))
            ]
        )
    )

    dialog_qr = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Container(ft.Text("QR-код", size=20, weight=ft.FontWeight.W_400), expand=True),
                ft.IconButton(ft.icons.CLOSE_ROUNDED, on_click=lambda _: close_dialog(dialog_qr))
            ]
        ),
        modal=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.ElevatedButton(text="Скопировать", icon=ft.icons.COPY_ROUNDED, color=ft.colors.WHITE)
        ]
    )

    loading_text = ft.Text("Загрузка", size=20, weight=ft.FontWeight.W_400)
    dialog_loading = ft.AlertDialog(
        # Диалог с кольцом загрузки

        # title=ft.Text(size=20),
        modal=True,
        content=ft.Column(
            controls=[
                ft.Column([loading_text, ft.ProgressBar()], alignment=ft.MainAxisAlignment.CENTER),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=400,
            height=50
        )
    )

    # Функции
    def open_dialog(dialog: ft.AlertDialog):
        page.dialog = dialog
        dialog.open = True
        page.update()

        if dialog == dialog_loading:
            time.sleep(1)

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
        # print(remaining_children_traffic)

    def update_modulecheck(mentor_id, module_name):
        query = "SELECT name from mentors WHERE id = %s"
        mentor_name = make_db_request(query, (mentor_id,), get_many=False)['name']

        if remaining_children_traffic:
            text = ""
            module_traffic_col.controls[2].controls.clear()
            for child_id in remaining_children_traffic:
                query = "SELECT * FROM children WHERE id = %s"
                child = make_db_request(query, (child_id,), get_many=False)
                module_traffic_col.controls[2].controls.append(
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(ft.Text(child['name'], size=18, weight=ft.FontWeight.W_300, width=300), expand=True),
                                ft.Checkbox(data=child['id'], on_change=modulecheck_checkbox_changed)
                            ]
                        ),
                        data=""
                    )
                )
                module_traffic_col.controls[2].controls.append(ft.Divider(thickness=1))
                text += f"({child['group_num']}) {child['name']}\n"

            open_sb(f"Осталось отметить: {len(remaining_children_traffic)}")
            message_text = f"*Посещаемость*" \
                           f"\n\nМодуль: *{module_name}*" \
                           f"\nСтатус: *не все 🏃*\n" \
                           f"{text}" \
                           f"\nОтметил: *{mentor_name}*"


        else:
            page.controls.clear()
            dialog_info.title.controls[0].content.value = "Посещаемость"
            dialog_info.content = ft.Text(f"Все дети на месте, спасибо! Можно возвращаться в телеграмм", size=18, width=600)
            open_dialog(dialog_info)

            message_text = f"*Посещаемость*" \
                           f"\n\nМодуль: *{module_name}*" \
                           f"\nСтатус: *все дети на месте ✅*" \
                           f"\n\nОтметил: *{mentor_name}*"
        send_telegam_message(os.getenv('ID_GROUP_MAIN'), message_text)
        page.update()

    def copy_qr_link(link):
        # копирование пригласительной ссылки

        page.set_clipboard(link)
        close_dialog(dialog_qr)
        open_sb("Ссылка скопирована")

    def show_qr(phrase):
        # показ диалога с qr-кодом

        if type(phrase) != str:
            phrase = phrase.control.data

        qr_path = f"assets/qrc/{phrase}.png"
        link = f"https://t.me/{os.getenv('BOT_NAME')}?start={phrase}"
        qr_img = qrcode.make(data=link)
        qr_img.save(qr_path)

        dialog_qr.content = ft.Image(src=f"qrc/{phrase}.png", border_radius=ft.border_radius.all(10), width=300)

        dialog_qr.actions[0].on_click = lambda _: copy_qr_link(link)
        page.dialog = dialog_qr
        dialog_qr.open = True
        page.update()

    def get_showqr(target: str, value: str = ""):
        titles = {
            'admins': "Администрация",
            'mentors': "Воспитатели",
            'teachers': "Преподаватели"
        }

        if target == "children":
            query = f"SELECT * FROM children WHERE group_num = %s AND telegram_id is null and status = 'active'"
            params = (value,)
            group_title = f"Группа №{value}"
        else:
            query = f"SELECT * FROM {target} WHERE telegram_id is NULL and status = 'active'"
            params = ()
            group_title = f"{titles[target]}"

        users_list = make_db_request(query, params, get_many=True)
        if users_list is not None:
            if users_list:
                qr_screen_col = ft.Column(width=600)
                users_col = ft.Column(width=600)

                for user in users_list:
                    users_col.controls.append(
                        ft.TextButton(
                            content=ft.Text(
                                value=user['name'],
                                size=18,
                                weight=ft.FontWeight.W_300
                            ),
                            on_click=lambda _: show_qr(f"{target}_{user['pass_phrase']}")
                        )
                    )
                    users_col.controls.append(ft.Divider(thickness=1))

                qr_screen_col.controls = [
                    ft.Card(
                        ft.Container(
                            ft.Column(
                                [ft.Text(f"{group_title}", size=18, weight=ft.FontWeight.W_500)],
                                width=page.width
                            ),
                            padding=15
                        )
                    ),
                    users_col
                ]
                page.add(qr_screen_col)
            else:
                dialog_info.title.controls[0].content.value = "QR-коды"
                dialog_info.content = ft.Text(f"В группе «{group_title}» все пользователи зарегистрированы", size=18, width=600)
                open_dialog(dialog_info)

    def get_modulecheck(mentor_id: str, module_id: str):

        query = "SELECT name FROM modules WHERE id = %s"
        module_info = make_db_request(query, (module_id,), get_many=False)

        query = "SELECT * FROM children WHERE id IN (SELECT child_id FROM modules_records WHERE module_id = %s)"
        children_list = make_db_request(query, (module_id,), get_many=True)
        if children_list is not None:

            children_list_col = ft.Column(width=600)
            children_list.sort(key=lambda el: el['name'])
            for child in children_list:
                remaining_children_traffic.append(child['id'])
                children_list_col.controls.append(
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(ft.Text(child['name'], size=18, weight=ft.FontWeight.W_300, width=300), expand=True),
                                ft.Checkbox(data=child['id'], on_change=modulecheck_checkbox_changed)
                            ]
                        ),
                        data=""
                    )
                )
                children_list_col.controls.append(ft.Divider(thickness=1))

            module_traffic_col.controls = [
                ft.Card(
                    ft.Container(
                        ft.Column(
                            [ft.Text(f"{module_info['name']}", size=18, weight=ft.FontWeight.W_500)],
                            width=page.width
                        ),
                        padding=15
                    ),
                    # elevation=10
                ),
                ft.Divider(thickness=1),
                children_list_col,
                ft.Row(
                    [ft.FilledTonalButton(text="Отправить", icon=ft.icons.SEND, on_click=lambda _: update_modulecheck(mentor_id, module_info['name']))],
                    alignment=ft.MainAxisAlignment.END
                )
            ]
            page.add(module_traffic_col)
        else:
            pass

    if platform.system() == "Windows":
        page.window_width = 377
        page.window_height = 768
        # page.route = "/modulecheck?mentor_id=1&module_id=1"
        # page.route = "/showqr?target=children&value=1"

    # Точка входа
    current_url = urlparse(page.route)
    url_params = parse_qs(current_url.query)
    if current_url.path == '/':
        if platform.system() == "Windows":
            change_screen("login")
        else:
            change_screen("login")

    elif current_url.path == '/modulecheck':
        # Отметка посещаемости
        change_screen("modulecheck", url_params)

    elif current_url.path == '/showqr':
        # Список qr-кодов
        change_screen("showqr", url_params)

    os.environ["FLET_SECRET_KEY"] = os.urandom(12).hex()
    page.update()


if __name__ == "__main__":
    if platform.system() == "Windows":
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
            # view=ft.AppView.WEB_BROWSER,
            port=8001
        )

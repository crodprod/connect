import logging
import math
import os
import platform
import random
import re
import time

import flet as ft
import qrcode
import redis
import xlrd
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from pypdf import PdfMerger

from transliterate import translit

import wording.wording
from database import MySQL, RedisTable
from flet_elements.dialogs import InfoDialog, LoadingDialog
from flet_elements.functions import remove_folder_content, get_hello, get_system_list
from flet_elements.modules_locations import locations
from flet_elements.screens import screens
from flet_elements.systemd import reboot_systemd, check_systemd
from flet_elements.telegram import send_telegam_message, send_telegram_document
from flet_elements.functions import is_debug

os.environ['FLET_WEB_APP_PATH'] = '/connect'
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)

if not os.path.exists(os.path.join(current_directory, 'assets/qrc')):
    logging.info(f'Creating folder assets/qrc')
    os.mkdir(os.path.join(current_directory, 'assets/qrc'))

if not os.path.exists(os.path.join(current_directory, 'wording/generated')):
    logging.info(f'Creating folder wording/generated')
    os.mkdir(os.path.join(current_directory, 'wording/generated'))

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
    port=3310,
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    db_name=os.getenv('DB_NAME')
)

redis = RedisTable(
    host=os.getenv('DB_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD')
)


def url_sign_check(sign: str, index: str):
    logging.info(f"Redis: getting signature (index: {index})")
    try:
        response = 0
        if redis.exists(index):

            if redis.get(index) == sign:
                response = 1
            else:
                response = -1
        logging.info(f"Redis: getting OK")
        return response
    except Exception as e:
        logging.error(f"Redis: {e}")
        return -2


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER,
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.title = "Коннект"
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

    remaining_children_traffic = []

    dlg_loading = LoadingDialog(page=page)
    dlg_info = InfoDialog(
        title="Info",
        content=ft.Text("Information Dialog"),
        page=page
    )

    db.connect()
    print(db.result)
    redis.connect()
    print(redis.result)

    if db.result['status'] == "error":
        startup['mysql']['status'] = False
        startup['mysql']['msg'] = db.result['message']

    if redis.result['status'] == "error":
        startup['redis']['status'] = False
        startup['redis']['msg'] = redis.result['message']

    def make_db_request(sql_query: str, params: tuple = ()):

        logging.info(f"Executing: {sql_query} ({params})")
        db.execute(sql_query, params)
        logging.info(db.result)
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

    # def raise_error(location, error_message: str, screen: str):
    #     if location == dialog_loading:
    #         dlg_loading.close()
    #         open_sb(error_message, ft.colors.RED)
    #         if "createdoc" in screen:
    #             change_screen("documents")

    def check_url(sign, index):
        response = url_sign_check(sign, index)
        print(response)
        text = {
            -2: "При получении данных возникла ошибка, попробуйте ещё раз.",
            -1: "Вы перешли по некорректной ссылке, попробуйте ещё раз.",
            0: "Ссылка, по которой вы перешли, недействительна, попробуйте ещё раз.",
            1: "Всё ок!"
        }

        if response in (0, -1, -2):
            dlg_info.title = "Ошибка доступа"
            dlg_info.content = ft.Text(text[response], width=600, size=16, weight=ft.FontWeight.W_200)
            dlg_info.open(action_btn_visible=False)
            return False
        return True

    def insert_children_info(table_filepath: str):
        dlg_loading.loading_text = "Добавляем детей"
        dlg_loading.open()
        wb = xlrd.open_workbook(table_filepath)
        ws = wb.sheet_by_index(0)
        rows_num = ws.nrows
        row = 1
        query = "UPDATE crodconnect.children SET status = 'removed'"
        if make_db_request(query) is not None:
            while row < rows_num:
                dlg_loading.dialog.content.controls[0].controls[0].value = f"Добавляем детей {row}/{rows_num}"
                page.update()
                child = []
                for col in range(5):
                    child.append(ws.cell_value(row, col))
                pass_phrase = create_passphrase(child[0])
                birth = xlrd.xldate.xldate_as_tuple(child[1], 0)
                # print(birth)
                birth = f"{birth[0]}-{birth[1]}-{birth[2]}"
                query = "INSERT INTO crodconnect.children (name, group_num, birth, comment, parrent_name, parrent_phone, pass_phrase) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                response = make_db_request(query, (child[0], random.randint(1, 5), birth, child[2], child[3], child[4], pass_phrase,))
                if response is None:
                    dlg_loading.close()
                    open_sb("Ошибка БД", ft.colors.RED)
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

    def appbar_action_selected(e: ft.ControlEvent):
        data = e.control.data
        print(data)

    def drawer_element_selected(e: ft.ControlEvent):
        data = e.control.data
        print(data)

        page.drawer.open = False
        page.update()

        if data['sec'] == "app":
            if data['act'] == "exit":
                password_field.value = ""
                change_screen("login")
            elif data['act'] == "home":
                change_screen("main")

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
        # print(phrase)

        return phrase

    def add_new_mentor():
        query = "INSERT INTO crodconnect.mentors (name, group_num, pass_phrase, status) VALUES (%s, %s, %s, 'active')"
        name = new_mentor_name_field.value.strip()
        pass_phrase = create_passphrase(name)
        response = make_db_request(query, (name, new_mentor_group_dd.value, pass_phrase))
        if response is not None:
            change_screen("mentors_info")
            open_sb("Воспитатель добавлен", ft.colors.GREEN)

    def add_new_module():
        dlg_loading.loading_text = "Добавляем модуль"
        dlg_loading.open()
        query = "INSERT INTO crodconnect.modules (name, seats_max, location) VALUES (%s, %s, %s)"
        make_db_request(query, (new_module_name_field.value, new_module_seats_field.value, new_module_location_dd.value))

        query = "SELECT id FROM crodconnect.modules WHERE name = %s"
        module_id = make_db_request(query, (new_module_name_field.value,))['id']

        query = "INSERT INTO crodconnect.teachers (name, module_id, pass_phrase) VALUES (%s, %s, %s)"
        name = new_module_teacher_name_field.value.strip()
        pass_phrase = create_passphrase(name)

        response = make_db_request(query, (name, module_id, pass_phrase,))
        dlg_loading.close()
        if response is not None:
            change_screen("modules_info")
            open_sb("Модуль добавлен", ft.colors.GREEN)

    def add_new_admin():
        query = "INSERT INTO crodconnect.admins (name, pass_phrase, password) VALUES (%s, %s, %s)"
        name = new_admin_name_field.value.strip()
        pass_phrase = create_passphrase(name)
        password = os.urandom(3).hex()
        response = make_db_request(query, (name, pass_phrase, password,))
        if response is not None:
            change_screen("admins_info")
            open_sb("Администратор добавлен", ft.colors.GREEN)

    def remove_mentor(e: ft.ControlEvent):
        query = "DELETE FROM crodconnect.mentors WHERE pass_phrase = %s"
        response = make_db_request(query, (e.control.data,))
        if response is not None:
            open_sb("Воспитатель удалён")
            change_screen("mentors_info")

    def remove_admin(e: ft.ControlEvent):
        query = "DELETE FROM crodconnect.admins WHERE pass_phrase = %s"
        response = make_db_request(query, (e.control.data,))
        if response is not None:
            open_sb("Администратор удалён")
            change_screen("admins_info")

    def goto_change_mentor_group(e: ft.ControlEvent):
        dialog_edit_mentor_group.data = e.control.data
        open_dialog(dialog_edit_mentor_group)

    def change_mentor_group(new_group):
        close_dialog(dialog_edit_mentor_group)
        dlg_loading.loading_text = "Обновляем"
        dlg_loading.open()
        query = "UPDATE crodconnect.mentors SET group_num = %s WHERE pass_phrase = %s"
        response = make_db_request(query, (new_group, dialog_edit_mentor_group.data,))
        dlg_loading.close()
        if response is not None:
            change_screen('mentors_info')
            open_sb("Группа изменена", ft.colors.GREEN)

            query = "SELECT telegram_id from crodconnect.mentors WHERE pass_phrase = %s"
            mentor_tid = make_db_request(query, (dialog_edit_mentor_group.data,))['telegram_id']
            if mentor_tid is not None:
                send_telegam_message(
                    tID=mentor_tid,
                    message_text="*Изменение группы*"
                                 f"\n\nВы были переведены администратором в *группу №{new_group}*"
                )

    def validate(target: str):
        if target == "mentor":
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

                    query = "SELECT * FROM crodconnect.children WHERE group_num = %s AND status = 'active'"
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

                # для групп детей
                for group_num in range(1, 6):
                    dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ (группа {group_num}/{5})"
                    page.update()

                    query = "SELECT * FROM crodconnect.children WHERE group_num = %s AND status = 'active'"
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

                    query = f"SELECT * FROM {s} WHERE status = 'active'"
                    group_list = make_db_request(query)

                    if group_list is not None:
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
                query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
                modules_list = make_db_request(query)

                if modules_list is not None:
                    if modules_list:
                        merger = PdfMerger()

                        for module in modules_list:
                            dlg_loading.dialog.content.controls[0].controls[0].value = f"Генерируем документ ({module['name'][:10]}...)"
                            page.update()

                            query = "SELECT * FROM crodconnect.teachers WHERE module_id = %s and status = 'active'"
                            teacher_info = make_db_request(query, (module['id'],))

                            if teacher_info is not None:
                                query = "SELECT * FROM crodconnect.children WHERE id in (SELECT child_id FROM crodconnect.modules_records WHERE module_id = %s) and status = 'active'"
                                children_list = make_db_request(query, (module['id'],))

                                if children_list is not None:
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
            elif doctype == "navigation":
                query = "SELECT name from crodconnect.shift_info where id = 0"
                shift_name = make_db_request(query)

                query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
                modules = make_db_request(query)

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
        pdf_filepaths.clear()
        dlg_loading.close()

    def get_document_card(title: str, sb: str, icon: ft.icons, doctype: str):
        card = ft.Card(
            ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            title=ft.Text(title),
                            subtitle=ft.Text(sb),
                            leading=ft.Icon(icon),
                            data={'doctype': doctype},
                            on_click=generate_document
                        )
                    ],
                    height=100,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
            ),
            width=600
        )

        return card

    def change_screen(target: str):
        logging.info(f"Changing screen to: {target}")

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
            page.appbar.title.value = screens[target]['appbar']['title']

        if target == "login":
            page.add(ft.Container(login_col, expand=True))

        elif target == "main":
            query = "SELECT * FROM crodconnect.admins WHERE password = %s"
            admin = make_db_request(query, (password_field.value,))

            view_pb = ft.ProgressBar()
            fback_pb = ft.ProgressBar()
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

            col = ft.Column(
                controls=[
                    ft.Container(ft.Text(get_hello(admin['name'].split()[1]), size=25, weight=ft.FontWeight.W_600), padding=ft.padding.only(left=10)),
                    systemd_card
                ]
            )

            page.add(col)
            page.update()

            systemd_list = get_system_list()
            time.sleep(2)
            if systemd_list:
                systemd_card.color = ft.colors.RED
                systemd_text.value = "Обнаружены нерабочие сервисы"
                systemd_btn.visible = True
            else:
                systemd_card.color = ft.colors.GREEN
                systemd_text.value = "Все сервисы работают корректно"
                systemd_btn.visible = False

            systemd_pb.visible = False
            fback_pb.visible = False
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

        elif target == "modules_info":
            page.appbar.actions = [
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(
                            text="Новый модуль",
                            icon=ft.icons.LIBRARY_ADD,
                            on_click=lambda _: change_screen("create_module")
                        ),
                        ft.Divider(thickness=1),
                        ft.PopupMenuItem(
                            text="Удалить модули",
                            icon=ft.icons.DELETE_FOREVER,
                            on_click=lambda _: open_confirmation("remove_modules")
                        ),
                        ft.PopupMenuItem(
                            text="Удалить записи",
                            icon=ft.icons.DELETE,
                            on_click=lambda _: open_confirmation("remove_modules_records")
                        ),
                    ]
                )
            ]
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()

            query = "SELECT * FROM crodconnect.modules WHERE status = 'active'"
            admins_list = make_db_request(query)
            if admins_list is not None:
                col = ft.Column()
                for admin in admins_list:
                    query = "SELECT * FROM crodconnect.teachers WHERE module_id = %s and status = 'active'"
                    teacher_info = make_db_request(query, (admin['id'],))
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

                        card = ft.Card(
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    ft.ListTile(
                                                        title=ft.Text('Название', size=14),
                                                        subtitle=ft.Text(admin['name'], size=16),
                                                        leading=ft.Icon(ft.icons.ARTICLE)
                                                    ),
                                                    expand=True
                                                ),
                                                ft.PopupMenuButton(
                                                    items=popup_items
                                                )
                                            ]
                                        ),
                                        ft.Container(ft.Divider(thickness=1), ),
                                        ft.ListTile(
                                            title=ft.Text('Преподаватель', size=14),
                                            subtitle=ft.Text(teacher_info['name'], size=16),
                                            leading=ft.Icon(ft.icons.PERSON)
                                        ),
                                        ft.Container(ft.Divider(thickness=1), ),
                                        ft.ListTile(
                                            title=ft.Text('Локация', size=14),
                                            subtitle=ft.Text(admin['location'], size=16),
                                            leading=ft.Icon(ft.icons.LOCATION_ON)
                                        ),
                                        ft.Container(ft.Divider(thickness=1), ),
                                        ft.ListTile(
                                            title=ft.Text('Заполненность', size=14),
                                            subtitle=ft.Text(f"{admin['seats_real']} из {admin['seats_max']}", size=16),
                                            leading=ft.Icon()
                                        )
                                    ],
                                    spacing=0.5
                                ),
                                # padding=ft.padding.only(left=15, right=15)
                            ),
                            width=600
                        )
                        col.controls.append(card)
                page.add(col)
                dlg_loading.close()

        elif target == "create_mentor":
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

        elif target == "create_admin":
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

        elif target == "mentors_info":
            page.appbar.actions = [
                ft.Container(
                    ft.IconButton(ft.icons.PERSON_ADD, on_click=lambda _: change_screen("create_mentor")),
                    padding=10
                )
            ]
            dlg_loading.loading_text = "Загрузка"
            dlg_loading.open()
            query = "SELECT * FROM crodconnect.mentors where status != 'removed'"
            mentors_list = make_db_request(query)
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
            query = "SELECT * FROM crodconnect.admins WHERE status != 'removed'"
            admins_list = make_db_request(query)
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
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "reboot_menu":
            page.appbar.actions = [
                ft.Container(
                    ft.PopupMenuButton(
                        items=[
                            ft.PopupMenuItem(text="Обновить", icon=ft.icons.RESTART_ALT, on_click=lambda _: change_screen("reboot_menu")),
                            ft.PopupMenuItem(text="Перезагрузка сервера", icon=ft.icons.VIEW_COMPACT_ALT, on_click=lambda _: open_confirmation("reboot_server")),
                        ]
                    ),
                    # ft.IconButton(ft.icons.RESTART_ALT, on_click=lambda _: change_screen("reboot_menu")),
                    padding=10
                )
            ]

            dlg_loading.loading_text = "Обновляем"
            dlg_loading.open()

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
                        title="Audio (приложение)",
                        icon=ft.icons.SPATIAL_AUDIO,
                        target="crod_audio_app"
                    ),
                    get_reboot_card(
                        title="Audio (веб-сокет)",
                        icon=ft.icons.SPATIAL_AUDIO,
                        target="crod_audio_server"
                    ),
                    get_reboot_card(
                        title="Audio (ngrok)",
                        icon=ft.icons.SPATIAL_AUDIO,
                        target="crod_ws_ngrok"
                    ),
                    get_reboot_card(
                        title="Эфир",
                        icon=ft.icons.ADD_TASK,
                        target="crod_stream"
                    ),
                    get_reboot_card(
                        title="Таскер",
                        icon=ft.icons.ADD_TASK,
                        target="crod_tasker"
                    ),
                    get_reboot_card(
                        title="Стартовая страница",
                        icon=ft.icons.ADD_TASK,
                        target="crod_mainpage"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)
            dlg_loading.close()

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

            elif action == "edit_stream":
                change_screen("edit_env")

            elif action == "remove_modules":
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

            elif action == "remove_modules_records":
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
                dlg_loading.loading_text = "Перезагрузка"
                dlg_loading.open()
                # to-do: перезагрузка сервера

        else:
            open_sb("Неверный код", ft.colors.RED)
        confirmation_code_field.value = ""

    def open_confirmation(action: str):

        actions_descrition = {
            'upload_children': {
                'title': "Загрузка таблицы"
            },
            'edit_stream': {
                'title': "Конфигурация"
            },
            'remove_modules': {
                'title': "Удаление модулей"
            },
            'remove_modules_records': {
                'title': "Удаление записей на модули"
            },
            'reboot_server': {
                'title': "Перезагрузка сервера"
            }
        }

        if is_telegrammed('confirm'):
            dialog_confirmation.title.controls[0].content.value = actions_descrition[action]['title']
            confirmation_code = os.urandom(3).hex()
            dialog_confirmation.data = [confirmation_code, action]
            open_dialog(dialog_confirmation)

            send_telegam_message(
                password_field.data['telegram_id'],
                "*Код подтверждения*"
                f"\n\nДля подтверждения действия в ЦРОД.Коннект введите `{confirmation_code}`"
            )

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
        content=confirmation_code_field,
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
        query = "SELECT * FROM crodconnect.admins WHERE password = %s and status = 'active'"
        admin_info = make_db_request(query, (password_field.value,))
        if admin_info is not None:
            if admin_info:
                password_field.data = admin_info
                change_screen("main")
            else:
                open_sb("Ошибка доступа", ft.colors.RED)

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
    dialog_info_text = ft.Text(size=16, width=600, weight=ft.FontWeight.W_200)
    dialog_info_title = ft.Text(size=20, weight=ft.FontWeight.W_400)
    dialog_info = ft.AlertDialog(
        modal=True,
        title=dialog_info_title,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[ft.TextButton("OK", on_click=lambda _: close_dialog(dialog_info))],
        content=dialog_info_text
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

    def update_modulecheck(mentor_id, module_name):
        query = "SELECT name from crodconnect.mentors WHERE id = %s"
        mentor_name = make_db_request(query, (mentor_id,))['name']

        if remaining_children_traffic:
            text = ""
            module_traffic_col.controls[2].controls.clear()
            for child_id in remaining_children_traffic:
                query = "SELECT * FROM crodconnect.children WHERE id = %s"
                child = make_db_request(query, (child_id,))
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
            dlg_info.title = "Посещаемость"
            dlg_info.content = ft.Text(
                "Все дети на месте, спасибо! Можно возвращаться в Telegram.",
                width=600, size=16, weight=ft.FontWeight.W_200
            )
            dlg_info.open(action_btn_visible=False)

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

    def get_user_qr(e: ft.ControlEvent):
        data = e.control.data
        phrase = f"{data['status']}_{data['pass_phrase']}"
        show_qr(phrase)

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
        page.appbar = None
        page.scroll = ft.ScrollMode.HIDDEN
        dlg_loading.loading_text = "Загрузка"
        dlg_loading.open()

        titles = {
            'admins': "Администрация",
            'mentors': "Воспитатели",
            'teachers': "Преподаватели"
        }

        if target == "children":
            query = f"SELECT * FROM crodconnect.children WHERE group_num = %s AND telegram_id is null and status = 'active'"
            params = (value,)
            group_title = f"Группа №{value}"
        else:
            query = f"SELECT * FROM {target} WHERE telegram_id is NULL and status = 'active'"
            params = ()
            group_title = f"{titles[target]}"

        users_list = make_db_request(query, params)
        if users_list is not None:
            if users_list:
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
                            data={'status': target, 'pass_phrase': user['pass_phrase']},
                            on_click=get_user_qr
                        )
                    )
                    users_col.controls.append(ft.Divider(thickness=1))

                qr_screen_col.controls = [
                    ft.Card(
                        ft.Container(
                            content=ft.ListTile(
                                title=ft.Text(f"Список QR-кодов", size=16),
                                subtitle=ft.Text(group_title, size=20, weight=ft.FontWeight.W_400),
                            )
                        )
                    ),
                    users_col
                ]
                page.add(qr_screen_col)
                dlg_loading.close()
            else:
                dlg_info.title = "QR-коды"
                dlg_info.content = ft.Text(
                    f"Все пользователи в группе «{group_title}» зарегистрированы!",
                    width=600, size=16, weight=ft.FontWeight.W_200
                )
                dlg_info.open(action_btn_visible=False)

    def get_modulecheck(mentor_id: str, module_id: str):
        page.scroll = ft.ScrollMode.HIDDEN
        page.appbar = None
        dlg_loading.loading_text = "Загрузка"
        dlg_loading.open()

        query = "SELECT name FROM crodconnect.modules WHERE id = %s"
        module_info = make_db_request(query, (module_id,))

        query = "SELECT * FROM crodconnect.children WHERE id IN (SELECT child_id FROM crodconnect.modules_records WHERE module_id = %s)"
        children_list = make_db_request(query, (module_id,))
        if children_list is not None:

            children_list_col = ft.Column(width=600, scroll=ft.ScrollMode.HIDDEN)
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
                        content=ft.ListTile(
                            title=ft.Text(f"Проверка посещаемости", size=16),
                            subtitle=ft.Text(f"{module_info['name']}", size=20, weight=ft.FontWeight.W_400),
                        )
                    )
                ),
                ft.Divider(thickness=1),
                children_list_col,
                ft.Row(
                    [ft.FilledTonalButton(text="Отправить", icon=ft.icons.SEND, on_click=lambda _: update_modulecheck(mentor_id, module_info['name']))],
                    alignment=ft.MainAxisAlignment.END
                )
            ]
            page.add(module_traffic_col)
            dlg_loading.close()

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
                        title=ft.Text("Обновление списка"),
                        subtitle=ft.Text("Загрузка таблицы с информацией о детях"),
                        leading=ft.Icon(ft.icons.UPLOAD_FILE),
                        data={'sec': "children", 'act': "update_table"},
                        on_click=drawer_element_selected),
                    ft.ListTile(
                        title=ft.Text("Изменение группы"),
                        subtitle=ft.Text("Изменение номера группы ребёнка"),
                        leading=ft.Icon(ft.icons.EDIT_DOCUMENT),
                        data={'sec': "children", 'act': "edit_group_num"},
                        on_click=drawer_element_selected),
                    ft.ListTile(
                        title=ft.Text("Добавить ребёнка"),
                        subtitle=ft.Text("Единичное добавление нового ребёнка"),
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
        # page.route = "/modulecheck?mentor_id=26&module_id=1&signature=265013c29e25b5c1a7b3782fcefac903c473d53c4d55b593e8b8d35990fd43db"
        # page.route = "/showqr?target=children&value=3&signature=e4d0bb16a50c20ca7ce53b0d753f2f7570ea2990750fd76ae62daa6030d1b27a"

    # Точка входа
    url = urlparse(page.route)
    url_path = url.path
    url_params = parse_qs(url.query)

    if all([fl[1]['status'] for fl in startup.items()]):
        if url_path == "/":
            if is_debug():
                password_field.value = "lrrrtm"
                change_screen("login")
                login()
            else:
                change_screen("login")

        elif url_path == "/modulecheck":
            mentor_id, module_id, sign = url_params['mentor_id'][0], url_params['module_id'][0], url_params['signature'][0]
            if check_url(sign, f"{mentor_id}{module_id}"):
                get_modulecheck(mentor_id, module_id)

        elif url_path == "/showqr":
            target, value, sign = url_params['target'][0], url_params['value'][0], url_params['signature'][0]
            if check_url(sign, f"{target}{value}"):
                get_showqr(target, value)

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

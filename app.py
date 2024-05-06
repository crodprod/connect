import logging
import math
import os
import platform
import time

import flet as ft
import qrcode
import xlrd
from dotenv import load_dotenv
from mysql.connector import connect, Error as sql_error
from urllib.parse import urlparse, parse_qs

from requests import post

from flet_elements.tabs import menu_tabs_config
from flet_elements.screens import screens

os.environ['FLET_WEB_APP_PATH'] = '/connect'
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


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

    # структры для хранения информации
    remaining_children_traffic = []

    def send_telegam_message(tID, message_text):
        # отправка текстовых сообщений в телеграмм

        url = f'https://api.telegram.org/bot{os.getenv("BOT_TOKEN")}/sendMessage'
        data = {'chat_id': tID, 'text': message_text, "parse_mode": "Markdown"}
        post(url=url, data=data)

    def make_db_request(sql_query: str, params: tuple = (), get_many: bool = None, put_many: bool = None):
        # обработка sql-запросов
        # to-do - сообщение об ошибке
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
                return None
                # elements.global_vars.DB_FAIL = True
                # logging.error(f"DATABASE REQUEST: {e}\n{sql_query}{params}")
                # if page.navigation_bar.selected_index != 3:
                #     page.floating_action_button = None
                #     show_error('db_request', labels['errors']['db_request'].format(elements.global_vars.ERROR_TEXT.split(":")[0]))
                #     elements.global_vars.DB_FAIL = False
                # return None
        else:
            return None
            # if page.navigation_bar.selected_index != 3:
            #     page.floating_action_button = None
            #     show_error('db_request', labels['errors']['db_request'].format(elements.global_vars.ERROR_TEXT.split(":")[0]))
            #     elements.global_vars.DB_FAIL = False
            #     return None

    def insert_children_info(table_filepath: str):

        wb = xlrd.open_workbook(table_filepath)
        ws = wb.sheet_by_index(0)
        rows_num = ws.nrows
        row = 1
        query = "UPDATE children SET status = 'archived'"
        if make_db_request(query, put_many=False) is not None:
            pass
        else:
            print('err 1')

    def get_menu_card(title: str, subtitle: str, icon, target_screen: str = "", type: str = ""):
        if type != "":
            card = ft.Card(
                ft.Container(
                    ft.ListTile(
                        title=ft.Text(title),
                        subtitle=ft.Text(subtitle),
                        leading=ft.Icon(icon)
                    ),
                    on_click=lambda _: open_confirmation(type)
                ),
                width=600
            )
        else:
            card = ft.Card(
                ft.Container(
                    ft.ListTile(
                        title=ft.Text(title),
                        subtitle=ft.Text(subtitle),
                        leading=ft.Icon(icon)
                    ),
                    on_click=lambda _: change_screen(target_screen)
                ),
                width=600
            )

        return card

    def change_screen(target: str, params: [] = None):
        # изменение экрана

        page.controls.clear()
        page.appbar.leading = None
        page.appbar.visible = True

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

        elif target == "main":
            page.add(main_menu_col)

        elif target == "children":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Обновление списка",
                        subtitle="Загрузка таблицы с информацией о детях",
                        icon=ft.icons.UPLOAD_FILE,
                        type="upload_children"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "modules":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Новый модуль",
                        subtitle="Создание нового модуля",
                        icon=ft.icons.ADD_CIRCLE,
                        target_screen="main"
                    ),
                    get_menu_card(
                        title="Текущие модули",
                        subtitle="Просмотр активных модулей",
                        icon=ft.icons.VIEW_MODULE,
                        target_screen="main"
                    ),
                    get_menu_card(
                        title="Архив",
                        subtitle="Просмотр архивированных модулей",
                        icon=ft.icons.ARCHIVE,
                        target_screen="main"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "mentors":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="Воспитатели",
                        subtitle="Управление воспитателями",
                        icon=ft.icons.EMOJI_PEOPLE,
                        target_screen="main"
                    ),
                    get_menu_card(
                        title="Администраторы",
                        subtitle="Управление администраторами",
                        icon=ft.icons.MANAGE_ACCOUNTS,
                        target_screen="main"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)

        elif target == "settings":
            col = ft.Column(
                controls=[
                    get_menu_card(
                        title="API-токен",
                        subtitle="Изменение токена телеграмм-бота",
                        icon=ft.icons.TELEGRAM,
                        # target_screen="main"
                        type="edit_botapi"
                    ),
                    get_menu_card(
                        title="Параметры смены",
                        subtitle="Изменение параметров текущей смены или потока",
                        icon=ft.icons.MANAGE_ACCOUNTS,
                        type="edit_stream"
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            page.add(col)


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

    def check_confirmation():
        user_code = confirmation_code_field.value
        close_dialog(dialog_confirmation)
        if dialog_confirmation.data[0] == user_code:
            open_sb("Действие подтверждено", ft.colors.GREEN)
            print(f"confirmed_{dialog_confirmation.data[1]}")
            # change_screen(f"confirmed_{dialog_confirmation.data[1]}")
        else:
            open_sb("Неверный код", ft.colors.RED)
        confirmation_code_field.value = ""

    def open_confirmation(action: str):
        actions_descrition = {
            'edit_botapi': {
                'title': "API-токен"
            },
            'upload_children': {
                'title': "Загрузка таблицы"
            },
            'edit_modules_count': {
                'title': "Количество модулей"
            },
            'edit_stream': {
                'title': "Параметры смены"
            },
        }

        dialog_confirmation.title.controls[0].content.value = actions_descrition[action]['title']
        confirmation_code = os.urandom(3).hex()
        dialog_confirmation.data = [confirmation_code, action]
        open_dialog(dialog_confirmation)
        send_telegam_message(
            password_field.data['telegram_id'],
            "*Код подтверждения*"
            f"\n\nДля подтверждения действия в Коннект введите `{confirmation_code}`"
        )
        # dialog_confirmation.content.controls[0].value = actions_descrition[action]['hint_text']

    confirmation_code_field = ft.TextField(hint_text="Защитный код")

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
                ft.Text("Для подтверждения действия введите защитный код из сообщения в телеграмме", size=18, weight=ft.FontWeight.W_200),
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
        query = "SELECT * FROM admins WHERE password = %s"
        admin_info = make_db_request(query, (password_field.value,), get_many=True)
        if admin_info is not None:
            if admin_info:
                name = " ".join(admin_info[0]['name'].split(" ")[1:])
                password_field.data = admin_info[0]
                open_sb(f"Здравствуйте, {name}")
                change_screen("main")
            else:
                open_sb("Неверный код доступа", ft.colors.RED)
        page.update()

    def change_navbar_tab(e):
        if type(e) == int:
            tab_index = e
        else:
            tab_index = e.control.selected_index

        page.controls.clear()
        page.appbar.title.value = menu_tabs_config[tab_index]['title']
        page.scroll = menu_tabs_config[tab_index]['scroll']

        if tab_index == 0:
            page.add(settings_col)
        elif tab_index == 1:
            page.add(ft.Text("Экран 2"))
        elif tab_index == 2:
            page.add(ft.Text("Экран 3"))
        elif tab_index == 3:
            page.add(ft.Text("Экран 4"))

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
            ft.Card(
                ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(menu_tabs_config[0]['icon']),
                        title=ft.Text(menu_tabs_config[0]['title'], size=20, weight=ft.FontWeight.W_200)
                    ),
                    on_click=lambda _: change_screen("children")),
                width=600),
            ft.Card(
                ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(menu_tabs_config[1]['icon']),
                        title=ft.Text(menu_tabs_config[1]['title'], size=20, weight=ft.FontWeight.W_200)
                    ),
                    on_click=lambda _: change_screen("modules")),
                width=600),
            ft.Card(
                ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(menu_tabs_config[2]['icon']),
                        title=ft.Text(menu_tabs_config[2]['title'], size=20, weight=ft.FontWeight.W_200)
                    ),
                    on_click=lambda _: change_screen("mentors")),
                width=600),
            ft.Card(
                ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(menu_tabs_config[3]['icon']),
                        title=ft.Text(menu_tabs_config[3]['title'], size=20, weight=ft.FontWeight.W_200)
                    ),
                    on_click=lambda _: change_screen("settings")),
                width=600)
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

    # Функции
    def open_dialog(dialog: ft.AlertDialog):
        page.dialog = dialog
        dialog.open = True
        page.update()

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

    def show_qr(phrase: str):
        # показ диалога с qr-кодом

        qr_path = f"assets/qrc/{phrase}.png"
        link = f"https://t.me/crod_connect_bot?start={phrase}"
        qr_img = qrcode.make(data=link)
        qr_img.save(qr_path)

        dialog_qr.content = ft.Image(src=f"qrc/{phrase}.png", border_radius=ft.border_radius.all(10))

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
            query = "SELECT * FROM children WHERE group_num = %s AND status != 'active'"
            params = (value,)
            group_title = f"Группа №{value}"
        else:
            query = f"SELECT * FROM {target} WHERE status != %s"
            params = ('active',)
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
        # page.route = "/showqr?target=mentors&value=-1"

    # Точка входа
    current_url = urlparse(page.route)
    url_params = parse_qs(current_url.query)
    if current_url.path == '/':
        change_screen("login")

    elif current_url.path == '/modulecheck':
        # Отметка посещаемости
        change_screen("modulecheck", url_params)

    elif current_url.path == '/showqr':
        # Список qr-кодов
        change_screen("showqr", url_params)

    page.update()


if __name__ == "__main__":
    if platform.system() == "Windows":
        ft.app(
            target=main,
            assets_dir='assets'
        )
    else:
        ft.app(
            target=main,
            assets_dir='assets',
            # view=ft.AppView.WEB_BROWSER,
            port=8001
        )

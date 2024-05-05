import logging
import math
import os
import platform
import time

import flet as ft
import qrcode
from dotenv import load_dotenv
from mysql.connector import connect, Error as sql_error
from urllib.parse import urlparse, parse_qs

from requests import post

from flet_elements.tabs import tabs_config
from flet_elements.navigation_bar import navbar
from flet_elements.appbar import appbar
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
    page.window_width = 377
    page.window_height = 768
    page.fonts = {
        "Geologica": "fonts/Geologica.ttf",
    }
    page.appbar = ft.AppBar(
        center_title=False,
        title=ft.Text(size=20, weight=ft.FontWeight.W_500),
        bgcolor=ft.colors.SURFACE_VARIANT
    )
    remaining_children_traffic = []

    def send_telegam_message(tID, message_text):
        url = f'https://api.telegram.org/bot{os.getenv("BOT_TOKEN")}/sendMessage'
        data = {'chat_id': tID, 'text': message_text, "parse_mode": "Markdown"}
        response = post(url=url, data=data)
        # print(response.json())

    def make_db_request(sql_query: str, params: tuple = (), get_many: bool = None, put_many: bool = None):
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
                # print(e)
                return None
                # elements.global_vars.DB_FAIL = True
                # logging.error(f"DATABASE REQUEST: {e}\n{sql_query}{params}")
                # if page.navigation_bar.selected_index != 3:
                #     page.floating_action_button = None
                #     show_error('db_request', labels['errors']['db_request'].format(elements.global_vars.ERROR_TEXT.split(":")[0]))
                #     elements.global_vars.DB_FAIL = False
                # return None
        else:
            # print('passed')
            return None
            # if page.navigation_bar.selected_index != 3:
            #     page.floating_action_button = None
            #     show_error('db_request', labels['errors']['db_request'].format(elements.global_vars.ERROR_TEXT.split(":")[0]))
            #     elements.global_vars.DB_FAIL = False
            #     return None

    def change_screen(target: str, params: [] = None):
        page.controls.clear()
        page.floating_action_button = None
        page.navigation_bar = None
        page.scroll = None
        page.appbar.title.value = screens[target]['title']
        print(screens[target]['title'])
        if target == "login":
            pass
        elif target == "main":
            change_navbar_tab(0)
        elif target == "showqr":
            get_showqr(group_num=params['group_id'][0])
        elif target == "modulecheck":
            get_modulecheck(mentor_id=params['mentor_id'][0], module_id=params['module_id'][0])

    def change_navbar_tab(e):
        if type(e) == int:
            tab_index = e
        else:
            tab_index = e.control.selected_index

        page.controls.clear()
        # page.appbar.leading = ft.IconButton(
        #     icon=screens['main']['lead_icon'],
        #     on_click=lambda _: change_screen('login'),
        #     rotate=math.pi
        # )
        # page.appbar.title.value = tabs_config[tab_index]['title']
        page.scroll = tabs_config[tab_index]['scroll']
        # page.appbar.actions = [
        #     ft.Container(
        #         ft.Row(tabs_config[tab_index]['actions']),
        #         margin=ft.margin.only(right=15)
        #     )
        # ]

        if tab_index == 0:
            page.add(settings_col)
        elif tab_index == 1:
            pass
        elif tab_index == 2:
            pass

        page.update()

    module_traffic_col = ft.Column(width=600)

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
            ft.ElevatedButton(text="Ссылка", icon=ft.icons.COPY_ROUNDED, color=ft.colors.WHITE),
            ft.ElevatedButton(text="Закрыть", on_click=lambda _: close_dialog(dialog_qr), color=ft.colors.WHITE)
        ]
    )

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
        page.set_clipboard(link)
        close_dialog(dialog_qr)
        open_sb("Ссылка скопирована")

    def show_qr(phrase: str):

        qr_path = f"assets/qrc/{phrase}.png"
        link = f"https://t.me/crod_connect_bot?start={phrase}"

        if phrase.split('_')[1] == "None":
            dialog_qr.content = ft.Text("Для данного пользователя не задана ключ-фраза", size=18)
        else:
            qr_img = qrcode.make(data=link)
            qr_img.save(qr_path)
        dialog_qr.content = ft.Column(
            [
                ft.Container(
                    ft.Image(src=f"qrc/{phrase}.png", border_radius=ft.border_radius.all(10)), width=300),
            ],
            # width=350,
            height=350,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        dialog_qr.actions[0].on_click = lambda _: copy_qr_link(link)
        page.dialog = dialog_qr
        dialog_qr.open = True
        page.update()

    def get_showqr(group_num: str):
        query = "SELECT * FROM children WHERE group_num = %s AND status != 'active'"
        children_list = make_db_request(query, (group_num,), get_many=True)
        # print(children_list)
        if children_list is not None:
            if children_list:
                col = ft.Column(width=600)
                children_col = ft.Column(width=600)
                for child in children_list:
                    children_col.controls.append(
                        ft.TextButton(content=ft.Text(child['name'], size=18, weight=ft.FontWeight.W_300), on_click=lambda _: show_qr(f"children_{child['pass_phrase']}"))
                    )
                    children_col.controls.append(ft.Divider(thickness=1))
                col.controls = [
                    ft.Card(
                        ft.Container(
                            ft.Column(
                                [ft.Text(f"Список детей без QR-кодов\nГруппа №{group_num}", size=18, weight=ft.FontWeight.W_500)],
                                width=page.width
                            ),
                            padding=15
                        )
                    ),
                    children_col
                ]
                page.add(col)
            else:
                dialog_info.title.controls[0].content.value = "QR-коды"
                dialog_info.content = ft.Text(f"В вашей группе все дети зарегистрированы", size=18, width=600)
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
                            [ft.Text(f"Модуль\n{module_info['name']}", size=18, weight=ft.FontWeight.W_500)],
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
        page.route = "/modulecheck?mentor_id=1&module_id=1"
        # page.route = "/showqr?group_id=1"
        # page.route = "/"

    current_url = urlparse(page.route)
    url_params = parse_qs(current_url.query)
    if current_url.path == '/':
        # page.navigation_bar = navbar
        # page.navigation_bar.on_change = change_navbar_tab
        change_screen("main")
    elif current_url.path == '/modulecheck':
        change_screen("modulecheck", url_params)
    elif current_url.path == '/showqr':
        change_screen("showqr", url_params)
    page.update()


if __name__ == "__main__":
    ft.app(
        target=main,
        assets_dir='assets',
        # upload_dir='assets/uploads',
        use_color_emoji=True,
        view=ft.AppView.WEB_BROWSER,
        port=8001
    )

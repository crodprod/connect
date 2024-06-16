import logging
import os
from urllib.parse import urlparse, parse_qs

import flet as ft

logging.basicConfig(level=logging.INFO)

errors = {
    '404': {
        'text': "Такой страницы не существует",
        'icon': ft.icons.PLAYLIST_REMOVE
    },
    '502': {
        'text': "Сервис временно недоступен, обновите страницу через несколько минут",
        'icon': ft.icons.HOURGLASS_BOTTOM
    },
    '405': {
        'text': "Такой запрос не поддерживается",
        'icon': ft.icons.CONNECT_WITHOUT_CONTACT
    },
}

os.environ['FLET_WEB_APP_PATH'] = '/connect'


def main(page: ft.Page):
    page.title = "Ошибка"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
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

    url = urlparse(page.route)
    url_path = url.path.split('/')[1:]

    print(url_path)
    if url_path[0] not in errors.keys():
        text = "Неизвестная ошибка"
        icon = ft.icons.ERROR
    else:
        text = errors[url_path[0]]['text']
        icon = errors[url_path[0]]['icon']

    col = ft.Column(
        [
            ft.Icon(icon, color=ft.colors.AMBER, size=100),
            ft.Text(text, size=18, weight=ft.FontWeight.W_200, text_align=ft.TextAlign.CENTER, width=500),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    page.add(ft.Container(col, expand=True))


if __name__ == '__main__':
    ft.app(
        target=main,
        port=8003,
        assets_dir='assets'
    )

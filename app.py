import os

import flet as ft

os.environ['FLET_WEB_APP_PATH'] = '/connect'


def main(page: ft.Page):
    page.title = "Connect"
    page.add(ft.Text("Это страница для Connect"))


if __name__ == "__main__":
    ft.app(main)

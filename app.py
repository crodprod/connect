import logging
import os

import flet as ft
from dotenv import load_dotenv
from mysql.connector import connect, Error as sql_error

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
    # page.vertical_alignment = ft.MainAxisAlignment.START,
    # page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
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

    # page.window_width = 377
    # page.window_height = 768

    def change_screen(target: str):
        page.controls.clear()
        page.floating_action_button = None
        page.scroll = None
        

if __name__ == "__main__":
    ft.app(
        target=main,
        assets_dir='assets',
        upload_dir='assets/uploads',
        use_color_emoji=True
    )

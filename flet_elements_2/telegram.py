from requests import post, exceptions
from os import getenv
from logging import basicConfig, info, error, INFO

basicConfig(
    level=INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def send_telegam_message(tID, message_text):
    # отправка текстовых сообщений в телеграмм

    info(f"Sending telegram message to {tID}")
    url = f'https://api.telegram.org/bot{getenv("BOT_TOKEN")}/sendMessage'
    data = {'chat_id': tID, 'text': message_text, "parse_mode": "Markdown"}
    response = post(url=url, data=data)
    info(response.json())


def send_telegram_document(tID, filepath: str, description: str):
    url = f'https://api.telegram.org/bot{getenv("BOT_TOKEN")}/sendDocument'

    with open(filepath, 'rb') as file:
        info(f"Sending telegram document to {tID}")
        files = {'document': file}
        data = {'chat_id': tID, 'caption': description, 'parse_mode': "Markdown"}
        try:
            response = post(url=url, data=data, files=files)
            info(info(response.json()))
            return True
        except exceptions.ConnectTimeout:
            return False

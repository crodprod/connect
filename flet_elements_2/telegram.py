from requests import post, exceptions
from os import getenv


def send_telegam_message(tID, message_text):
    # отправка текстовых сообщений в телеграмм

    url = f'https://api.telegram.org/bot{getenv("BOT_TOKEN")}/sendMessage'
    data = {'chat_id': tID, 'text': message_text, "parse_mode": "Markdown"}
    response = post(url=url, data=data)


def send_telegram_document(tID, filepath: str, description: str):
    url = f'https://api.telegram.org/bot{getenv("BOT_TOKEN")}/sendDocument'

    with open(filepath, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': tID, 'caption': description, 'parse_mode': "Markdown"}
        try:
            post(url=url, data=data, files=files)
            return True
        except exceptions.ConnectTimeout:
            return False

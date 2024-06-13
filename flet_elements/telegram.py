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
    if response.status_code == 200:
        return {'chat_id': response.json()['result']['chat']['id'], 'message_id': response.json()['result']['message_id']}
    else:
        return False


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


def delete_telegram_message(data):
    url = f'https://api.telegram.org/bot{getenv("BOT_TOKEN")}/deleteMessage'
    data = {'chat_id': data['chat_id'], 'message_id': data['message_id']}
    try:
        response = post(url=url, data=data)
    except Exception as e:
        error(f"deleting message: {e}")
        return False
    return True

import os
import platform
import subprocess

import schedule
import time
from datetime import datetime

from dotenv import load_dotenv

import yadiskapi
from flet_elements.telegram import send_telegam_message

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"

load_dotenv(dotenv_path=env_path)
print(os.getenv('YANDEX_REST_URL'))
yandex = yadiskapi.YandexAPI(os.getenv('YANDEX_REST_URL'), os.getenv('YANDEX_REST_TOKEN'))


def mysql_backup():
    filename = f"crodconnect_backup_{datetime.now().strftime('%Y-%m-%d-%H-%M')}.sql"
    filepath = f"/root/crod/{filename}"

    command = f"mysqldump -h 127.0.0.1 -P {3310} -u {os.getenv('DB_USER')} -p{os.getenv('DB_PASSWORD')} crodconnect > {filepath}"

    text = f"*Статус:* ✅ создан" \
           f"\n*Файл:* {filename}"

    try:
        subprocess.run(command)

        response = yandex.get_upload_link(f'CROD_MEDIA/Бекапы/{filename}')
        if 'href' in response.keys():
            yandex.upload_file(
                url=response['href'],
                filepath=filepath
            )

        else:
            text = f"*Статус:* ⛔ не создан" \
                   f"\n*Ошибка:* {response['message']}"

    except Exception as e:
        text = f"*Статус:* ⛔ не создан" \
               f"\n*Ошибка:* {e}"

    send_telegam_message(
        tID=os.getenv('ID_GROUP_ERRORS'),
        message_text=f"*Бекап базы данных*\n\n{text}"
    )


schedule.every().day.at("02:23").do(mysql_backup)

while True:
    schedule.run_pending()
    time.sleep(1)

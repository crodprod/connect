import platform
import yadiskapi
import logging
import subprocess
from datetime import datetime
import os
from flet_elements.telegram import send_telegam_message


def mysql_backup():
    if platform.system() == "Linux":
        yandex = yadiskapi.YandexAPI(os.getenv('YANDEX_REST_URL'), os.getenv('YANDEX_REST_TOKEN'))
        logging.info('Backup: wake up')
        filename = f"crodconnect_backup_{datetime.now().strftime('%Y-%m-%d-%H-%M')}.sql"
        filepath = f"/root/crod/backups/{filename}"
        logging.info(f'Backup: creating {filename}')

        command = f"/usr/bin/mysqldump -h 127.0.0.1 -P {3310} -u {os.getenv('DB_USER')} -p{os.getenv('DB_PASSWORD')} crodconnect > {filepath}"

        text = f"*Статус:* ✅ создан" \
               f"\n*Файл:* {filename}"

        try:
            logging.info('Backup: running subprocess')
            subprocess.run(command, shell=True)

            logging.info('Backup: getting upload link')
            response = yandex.get_upload_link(f'CROD_MEDIA/Бекапы/{filename}')
            if 'href' in response.keys():
                logging.info('Backup: upload link recieved, uploading file')
                yandex.upload_file(
                    url=response['href'],
                    filepath=filepath
                )
                logging.info('Backup: file uploaded to Yandex.Disk')

            else:
                logging.error(f"Backup: upload link recieve failed: {response['message']}")
                text = f"*Статус:* ⛔ не создан" \
                       f"\n*Ошибка:* {response['message']}"

        except Exception as e:
            logging.error(f"Backup: {e}")
            text = f"*Статус:* ⛔ не создан" \
                   f"\n*Ошибка:* {e}"

    else:
        text = f"*Статус:* отладка"

    send_telegam_message(
        tID=os.getenv('ID_GROUP_ERRORS'),
        message_text=f"*Бекап базы данных*\n\n{text}\n\n#бекап"
    )

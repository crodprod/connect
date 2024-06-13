import os
import platform
import schedule
import time
import logging

from dotenv import load_dotenv
from flet_elements.telegram import send_telegam_message
from backup import mysql_backup

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"

load_dotenv(dotenv_path=env_path)

backup_time = os.getenv('DB_BACKUP_TIME')
logging.info(f'Backup: time to backup is {backup_time}')


schedule.every().day.at(backup_time).do(mysql_backup)

send_telegam_message(
    tID=os.getenv('ID_GROUP_ERRORS'),
    message_text=f"*Бекап базы данных*"
                 f"\n\nАвтоматический бекап ежедневно в {backup_time}\n\n#бекап"
)

logging.info('Scheduler: started')
while True:
    schedule.run_pending()
    time.sleep(1)

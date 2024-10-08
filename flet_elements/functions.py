import os
import platform
from os import listdir, path, unlink, getenv
from shutil import rmtree
from datetime import datetime

from flet_elements.systemd import check_systemd, services_list


def remove_folder_content(filepath):
    for filename in listdir(filepath):
        file_path = path.join(filepath, filename)
        try:
            if path.isfile(file_path) or path.islink(file_path):
                unlink(file_path)
            elif path.isdir(file_path):
                rmtree(file_path)
        except Exception as e:
            pass


def get_hello(name):
    hour = datetime.now().hour
    if 0 <= hour < 6:
        text = "Доброй ночи"
    elif 6 <= hour < 12:
        text = "Доброе утро"
    elif 12 <= hour < 18:
        text = "Добрый день"
    elif 18 <= hour < 24:
        text = "Добрый вечер"

    return f"{text}, \n{name}!"


def get_system_list():
    not_working = []

    for service in services_list:
        if is_debug() or platform.system() == "Windows":
            not_working.append(service)
        else:
            if not check_systemd(service):
                not_working.append(service)

    return not_working


def is_debug():
    if getenv("DEBUG", 'False').lower() in ('true', '1', 't'):
        return True
    return False
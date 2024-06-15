import platform
from subprocess import Popen, PIPE

systemctl_path = "/usr/bin/systemctl"

services_list = [
    {
        'title': "Бот",
        'service': "crod_connect_bot"
    },
    {
        'title': "Коннект",
        'service': "crod_connect"
    },
    {
        'title': "Audio (приложение)",
        'service': "crod_audio_app"
    },
    {
        'title': "Audio (веб-сокет)",
        'service': "crod_audio_server"
    },
    {
        'title': "Audio (ngrok)",
        'service': "crod_ws_ngrok"
    },
    {
        'title': "Эфир",
        'service': "crod_stream"
    },
    {
        'title': "Таскер",
        'service': "crod_tasker"
    },
    {
        'title': "Стартовая страница",
        'service': "crod_mainpage"
    },
    {
        'title': "Flask",
        'service': "flask"
    }
]


def check_systemd(service_name: str) -> bool():
    if platform.system() == "Windows":
        return False

    command = [systemctl_path, 'status', f'{service_name}.service']
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    if process.returncode == 0:
        text = output.decode()
        if text[text.find('Active:') + 8:].split()[0] == 'active':
            return True
        return False
    else:
        return False


def reboot_systemd(service_name: str):
    if platform.system() == "Windows":
        return False
    command = [systemctl_path, 'restart', f'{service_name}.service']
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    if process.returncode != 0:
        return False
    return True

import platform
from subprocess import Popen, PIPE, run

systemctl_path = "/usr/bin/systemctl"

services_list = [
    {
        'title': "Бот",
        'service': "crod_connect_bot",
        'folder': '/connect'
    },
    {
        'title': "Коннект",
        'service': "crod_connect",
        'folder': '/connect'
    },
    {
        'title': "Audio (приложение)",
        'service': "crod_audio_app",
        'folder': '/audio'
    },
    {
        'title': "Audio (веб-сокет)",
        'service': "crod_audio_server",
        'folder': '/audio'
    },
    {
        'title': "Audio (ngrok)",
        'service': "crod_ws_ngrok",
        'folder': '/audio'
    },
    {
        'title': "Эфир",
        'service': "crod_stream",
        'folder': '/stream'
    },
    {
        'title': "Таскер",
        'service': "crod_tasker",
        'folder': '/tasker'
    },
    {
        'title': "Стартовая страница",
        'service': "crod_mainpage",
        'folder': '/loginscreen'
    },
    {
        'title': "Flask",
        'service': "flask",
        'folder': '/connect'
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


def get_service_info(service_name):
    for service in services_list:
        if service['service'] == service_name:
            return service


def make_update(service_name):
    service = get_service_info(service_name)
    source = "/root/crod" + service['folder']

    command = (
        f"cd {source} && "
        f"/usr/bin/git pull origin main && "
        f"source venv/bin/activate && "
        f"pip3 install -r requirements.txt && "
        f"deactivate && "
        f"cd && "
        f"/usr/bin/systemctl restart {service_name}.service"
    )

    try:
        run(command, shell=True)
        return {'status': 'ok', 'msg': f'Запрос на обновление сервиса {service_name} выполнен успешно.'}
    except Exception as e:
        return {'status': 'error', 'msg': f'Ошибка при выполнении запроса: {e}'}


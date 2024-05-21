from subprocess import Popen, PIPE

systemctl_path = "/usr/bin/systemctl"

services_list = [
    'crod_connect_bot',
    'crod_connect',
    'crod_audio_app',
    'crod_audio_server',
    'crod_ws_ngrok',
    'crod_tasker',
    'crod_mainpage',
]


def check_systemd(service_name: str) -> bool():
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
    command = [systemctl_path, 'restart', f'{service_name}.service']
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    if process.returncode != 0:
        return False
    return True

import os
import platform

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from flet_elements.telegram import send_telegam_message

app = Flask(__name__)

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)


@app.route('/addticket', methods=['POST'])
def add_ticket():
    ticket_data = request.json['params']
    # print(ticket_data)

    ticket_data['caption'] = 'отсутствует' if not ticket_data['caption'] else ticket_data['caption']
    ticket_data['file'] = 'отсутствует' if not ticket_data['file'] else f"[открыть]({ticket_data['file']})"

    send_telegam_message(
        tID=os.getenv('ID_GROUP_ERRORS'),
        message_text=f"*Обращение от пользователя*"
                     f"\n\n*Пользователь:* {123}"
                     f"\n*Проблема:* {ticket_data['topic']}"
                     f"\n*Описание:* {ticket_data['caption']}"

                     f"\n\n[Открыть ответ]({ticket_data['answer_link']})"
    )

    return jsonify({
        'status': 'success',
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

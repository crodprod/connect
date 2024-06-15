import os
import platform

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from database import MySQL
from flet_elements.telegram import send_telegam_message

app = Flask(__name__)

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)

db = MySQL(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    db_name=os.getenv('DB_NAME')
)


@app.route('/addticket', methods=['POST'])
def add_ticket():
    ticket_data = request.json['params']

    ticket_data['caption'] = 'отсутствует' if not ticket_data['caption'] else ticket_data['caption']
    ticket_data['file'] = 'отсутствует' if not ticket_data['file'] else f"[открыть]({ticket_data['file']})"
    user_tid = ticket_data['ticket_id'].split('-')[0]

    db.connect()
    query = """
            SELECT 'children' AS post_, name, status FROM crodconnect.children WHERE telegram_id = %s
            UNION
            SELECT 'teachers' AS post_, name, status FROM crodconnect.teachers WHERE telegram_id = %s
            UNION
            SELECT 'mentors' AS post_, name, status FROM crodconnect.mentors WHERE telegram_id = %s
            UNION 
            SELECT 'admins' AS post_, name, status FROM crodconnect.admins WHERE telegram_id = %s;
                """

    response = db.execute(query, (user_tid, user_tid, user_tid, user_tid,))
    db.disconnect()

    if db.result['status'] == 'ok':
        if response is None:
            user = "Информация в системе отсутствует"
        else:
            user = f"{response['name']}\nРоль: {response['post_']}\nСтатус: {response['status']}"
    else:
        user = "Не удалось получить информацию о пользователе"

    send_telegam_message(
        tID=os.getenv('ID_GROUP_ERRORS'),
        message_text=f"*Обращение от пользователя*"
                     f"\n\n*Пользователь:* \n{user}"
                     f"\n\n*Проблема:* {ticket_data['topic']}"
                     f"\n*Описание:* {ticket_data['caption']}"
                     f"\n*Файл:* {ticket_data['file']}"

                     f"\n\n[Открыть ответ]({ticket_data['answer_link']})"
    )

    return jsonify({
        'status': 'success',
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

import hmac
import hashlib
import platform
import urllib.parse
import time
import os

import redis
from dotenv import load_dotenv

if platform.system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)

url = 'https://crodconnect.ru/connect/modulecheck?mentor_id=26&module_id=1'
#
def generate_signature(url, secret_key):
    hmac_obj = hmac.new(secret_key.encode(), url.encode(), hashlib.sha256)
    signature = hmac_obj.hexdigest()
    return signature

def generate_signed_url(url, secret_key):
    # Добавляем временную метку к URL
    timestamp = int(time.time())
    url_with_timestamp = f"{url}&timestamp={timestamp}"

    # Генерируем подпись для URL с временной меткой
    signature = generate_signature(url_with_timestamp, secret_key)

    # Добавляем подпись к URL
    signed_url = f"{url}&signature={signature}"
    return signature

signature = generate_signed_url(url, os.getenv('SECRET_KEY'))
print("Signed URL:", signature)


redis_client = redis.StrictRedis(
    host=os.getenv('DB_HOST'),  # Замените на IP-адрес вашего сервера
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD'),  # Установите пароль, если вы его настроили
    decode_responses=True
)


redis_client.set('261', signature, 20)



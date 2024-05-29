import hashlib
import hmac
import time


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
    return [signed_url, signature]

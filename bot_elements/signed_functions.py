import hashlib
import hmac
import time
from logging import info


def create_signed_url(base_url: str, secret_key: str):
    info(f'Creating signature for url: {base_url}')
    hmac_obj = hmac.new(secret_key.encode(), f"{base_url}&timestamp={int(time.time())}".encode(), hashlib.sha256)
    signature = hmac_obj.hexdigest()
    url = f"{base_url}&signature={signature}"
    info(f'Signature created: {url}')
    return signature, url
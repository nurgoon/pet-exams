from __future__ import annotations

import hashlib
import os
import random
import re
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from django.utils import timezone


PHONE_DIGITS_RE = re.compile(r'\D+')


def normalize_phone(raw: str) -> Optional[str]:
    digits = PHONE_DIGITS_RE.sub('', raw or '')
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits
    if len(digits) != 11 or not digits.startswith('7'):
        return None
    return f'+{digits}'


def generate_sms_code(length: int = 4) -> str:
    length = max(4, min(length, 8))
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))


def hash_sms_code(phone: str, code: str) -> str:
    secret = os.getenv('DJANGO_SECRET_KEY', 'dev-only-secret-key-change-me')
    payload = f'{secret}:{phone}:{code}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def can_send_sms(last_sent_at, cooldown_seconds: int) -> bool:
    if not last_sent_at:
        return True
    return timezone.now() - last_sent_at >= timedelta(seconds=cooldown_seconds)


def send_sms_ru(*, api_key: str, sender: str, phone: str, message: str, timeout: int = 8) -> str:
    params = {
        'api_id': api_key,
        'to': phone,
        'msg': message,
    }
    if sender:
        params['from'] = sender
    url = f'https://sms.ru/sms/send?{urlencode(params)}'
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode('utf-8').strip()

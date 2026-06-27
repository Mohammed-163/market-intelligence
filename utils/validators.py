"""
validators.py
Input validation helpers.
"""
import re
from typing import Any


def validate_username(username: str, platform: str = "instagram") -> bool:
    if not username or not isinstance(username, str):
        return False
    username = username.strip().lstrip("@")
    if platform == "instagram":
        return bool(re.match(r'^[a-zA-Z0-9._]{1,30}$', username))
    elif platform == "tiktok":
        return bool(re.match(r'^[a-zA-Z0-9._]{1,24}$', username))
    elif platform == "youtube":
        return bool(re.match(r'^UC[\w-]{22}$', username)) or len(username) > 0
    return len(username) > 0


def validate_channel_id(channel_id: str) -> bool:
    return bool(re.match(r'^UC[\w-]{22}$', channel_id))


def is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def clean_username(username: str) -> str:
    return username.strip().lstrip("@")

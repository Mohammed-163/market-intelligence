"""
date_utils.py
Timestamp parsing and date utility helpers.
"""
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def parse_timestamp(raw) -> Optional[datetime]:
    """Parse a timestamp string or Unix epoch into a datetime object."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.utcfromtimestamp(raw)
        except Exception:
            return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(str(raw), fmt)
        except ValueError:
            continue
    logger.debug(f"Could not parse timestamp: {raw}")
    return None


def days_ago(dt: datetime) -> int:
    return (datetime.utcnow() - dt).days


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    return dt.strftime(fmt)

import sqlite3
import json
import time
from typing import Any, Optional

class Cache:
    def __init__(self, db_path: str, ttl_days: int):
        self.db_path = db_path
        self.ttl_seconds = ttl_days * 86400
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp REAL
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def get(self, key: str) -> Optional[Any]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute('SELECT data, timestamp FROM api_cache WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                data, timestamp = row
                if time.time() - timestamp < self.ttl_seconds:
                    return json.loads(data)
                else:
                    conn.execute('DELETE FROM api_cache WHERE key = ?', (key,))
                    conn.commit()
            return None
        finally:
            conn.close()

    def set(self, key: str, data: Any) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                INSERT OR REPLACE INTO api_cache (key, data, timestamp)
                VALUES (?, ?, ?)
            ''', (key, json.dumps(data), time.time()))
            conn.commit()
        finally:
            conn.close()

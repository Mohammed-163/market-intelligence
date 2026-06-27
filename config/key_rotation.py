import threading
from typing import List, Tuple

class AllKeysExhaustedException(Exception):
    pass

class KeyRotator:
    def __init__(self, pool_name: str, keys: Tuple[str, ...] | List[str]):
        if not keys:
            raise ValueError("Keys cannot be empty")
        self.pool_name = pool_name
        self._keys = list(keys)
        self._failed = [False] * len(keys)
        self._current_index = 0
        self._lock = threading.Lock()

    def get_current_key(self) -> str:
        with self._lock:
            for i in range(len(self._keys)):
                idx = (self._current_index + i) % len(self._keys)
                if not self._failed[idx]:
                    self._current_index = idx
                    return self._keys[idx]
            raise AllKeysExhaustedException(f"All keys exhausted for {self.pool_name}")

    def mark_key_failed(self, key: str, reason: str = "") -> str:
        with self._lock:
            try:
                idx = self._keys.index(key)
                self._failed[idx] = True
            except ValueError:
                pass
            
            # Find next
            for i in range(len(self._keys)):
                next_idx = (self._current_index + i) % len(self._keys)
                if not self._failed[next_idx]:
                    self._current_index = next_idx
                    return self._keys[next_idx]
            
            raise AllKeysExhaustedException(f"All keys exhausted for {self.pool_name}")

import functools
import time
from typing import Callable, Any, Optional
from config.key_rotation import KeyRotator, AllKeysExhaustedException
from config.constants import MAX_RETRIES, RETRY_BASE_DELAY_SECONDS, RETRY_MAX_DELAY_SECONDS
from utils.logger import get_logger

logger = get_logger()

def with_retry(rotator: Optional[KeyRotator] = None, error_patterns: frozenset = frozenset(), http_codes: frozenset = frozenset()):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while attempt < MAX_RETRIES:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    needs_rotation = False
                    for pattern in error_patterns:
                        if pattern.lower() in error_msg:
                            needs_rotation = True
                            break
                            
                    if not needs_rotation and hasattr(e, 'status_code') and e.status_code in http_codes:
                        needs_rotation = True
                    if not needs_rotation and hasattr(e, 'resp') and hasattr(e.resp, 'status') and getattr(e.resp, 'status') in http_codes:
                        needs_rotation = True
                    if not needs_rotation and hasattr(e, 'code') and getattr(e, 'code') in http_codes:
                        needs_rotation = True

                    if needs_rotation and rotator:
                        try:
                            old_key = rotator.get_current_key()
                            new_key = rotator.mark_key_failed(old_key, str(e)[:50])
                            logger.warning(f"Key rotated for {rotator.pool_name}. Retry {attempt+1}/{MAX_RETRIES}.")
                        except AllKeysExhaustedException as rot_e:
                            logger.error(f"All keys exhausted for {rotator.pool_name}")
                            raise rot_e
                    else:
                        logger.warning(f"Non-rotation error: {e}. Retry {attempt+1}/{MAX_RETRIES}.")
                    
                    attempt += 1
                    if attempt >= MAX_RETRIES:
                        raise e
                    
                    delay = min(RETRY_MAX_DELAY_SECONDS, RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

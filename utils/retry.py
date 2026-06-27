"""
retry.py
Generic retry decorator with optional key rotation on 429/5xx/quota errors.
"""
import functools
import time
from typing import Callable, Any, Optional, FrozenSet
from config.key_rotation import KeyRotator, AllKeysExhaustedException
from config.constants import MAX_RETRIES, RETRY_BASE_DELAY_SECONDS, RETRY_MAX_DELAY_SECONDS
from utils.logger import get_logger

logger = get_logger()


def with_retry(
    rotator: Optional[KeyRotator] = None,
    error_patterns: FrozenSet[str] = frozenset(),
    http_codes: FrozenSet[int] = frozenset(),
    rotator_attr: str = "rotator"
):
    """
    Decorator that retries a function up to MAX_RETRIES times.

    - If the exception matches a quota/rate-limit pattern the rotator (if provided)
      is used to switch to the next API key before retrying.
    - If no rotator is given the function still retries with exponential back-off.

    NOTE: When used on instance methods, pass rotator=None here and let the method
    access self.rotator directly inside its body. This avoids the module-level
    binding issue where the rotator is None at import time.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Resolve rotator: prefer explicit param, then self.rotator if available
            _rotator = rotator
            if _rotator is None and args and hasattr(args[0], rotator_attr):
                _rotator = getattr(args[0], rotator_attr)

            attempt = 0
            while attempt < MAX_RETRIES:
                try:
                    return func(*args, **kwargs)
                except AllKeysExhaustedException:
                    raise
                except Exception as e:
                    err_str = str(e).lower()

                    needs_rotation = (
                        any(p.lower() in err_str for p in error_patterns)
                        or (hasattr(e, "status_code") and e.status_code in http_codes)
                        or (hasattr(e, "resp") and getattr(e.resp, "status", None) in http_codes)
                        or (hasattr(e, "code") and getattr(e, "code", None) in http_codes)
                    )

                    if needs_rotation and _rotator:
                        try:
                            old = _rotator.get_current_key()
                            _rotator.mark_key_failed(old, str(e)[:60])
                            logger.warning(
                                f"Key rotated for {_rotator.pool_name}. "
                                f"Retry {attempt + 1}/{MAX_RETRIES}."
                            )
                        except AllKeysExhaustedException as ex:
                            logger.error(f"All keys exhausted for {_rotator.pool_name}")
                            raise ex
                    else:
                        logger.warning(f"Non-rotation error: {e}. Retry {attempt + 1}/{MAX_RETRIES}.")

                    attempt += 1
                    if attempt >= MAX_RETRIES:
                        raise

                    delay = min(
                        RETRY_MAX_DELAY_SECONDS,
                        RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    )
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

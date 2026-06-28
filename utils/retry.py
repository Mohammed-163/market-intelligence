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
    Decorator that retries a function up to effective_retries times,
    where effective_retries = max(MAX_RETRIES, number_of_available_keys).
    This ensures every key is tried regardless of MAX_RETRIES value.

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
            # Resolve rotator: prefer explicit param, then self.<rotator_attr> if available
            _rotator = rotator
            if _rotator is None and args and hasattr(args[0], rotator_attr):
                _rotator = getattr(args[0], rotator_attr)

            # Compute effective retries dynamically — always enough to try every key
            num_keys = len(_rotator._keys) if _rotator else 1
            effective_retries = max(MAX_RETRIES, num_keys)

            if _rotator:
                pool = _rotator.pool_name
                logger.info(
                    f"[{pool}] Starting request with {num_keys} key(s) available. "
                    f"Max attempts: {effective_retries}."
                )

            attempt = 0
            while attempt < effective_retries:
                # Log which key is being used (1-indexed)
                if _rotator:
                    try:
                        current_key = _rotator.get_current_key()
                        key_index = _rotator._keys.index(current_key) + 1
                        logger.info(f"[{_rotator.pool_name}] Using key #{key_index} (of {num_keys})")
                    except AllKeysExhaustedException:
                        raise
                    except Exception:
                        pass  # If index lookup fails, continue silently

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
                        or (hasattr(e, "code") and getattr(e, "code\n", None) in http_codes)
                    )

                    if needs_rotation and _rotator:
                        try:
                            old_key = _rotator.get_current_key()
                            old_index = _rotator._keys.index(old_key) + 1
                            _rotator.mark_key_failed(old_key, str(e)[:60])
                            try:
                                next_key = _rotator.get_current_key()
                                next_index = _rotator._keys.index(next_key) + 1
                                logger.warning(
                                    f"[{_rotator.pool_name}] Key #{old_index} exhausted "
                                    f"({str(e)[:60]}). Switching to key #{next_index}."
                                )
                            except AllKeysExhaustedException:
                                logger.error(
                                    f"[{_rotator.pool_name}] Key #{old_index} exhausted. "
                                    f"All {num_keys} keys exhausted. No more keys to try."
                                )
                                raise AllKeysExhaustedException(
                                    f"All {num_keys} keys exhausted for {_rotator.pool_name}"
                                )
                        except AllKeysExhaustedException:
                            raise
                    else:
                        logger.warning(
                            f"[{_rotator.pool_name if _rotator else 'unknown'}] "
                            f"Non-rotation error: {e}. Retry {attempt + 1}/{effective_retries}."
                        )

                    attempt += 1
                    if attempt >= effective_retries:
                        raise

                    delay = min(
                        RETRY_MAX_DELAY_SECONDS,
                        RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    )
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

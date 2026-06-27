"""
apify_service.py
Single abstraction layer for all Apify actor calls and dataset reads.
"""
from apify_client import ApifyClient
from config.key_rotation import KeyRotator, AllKeysExhaustedException
from config.constants import APIFY_ROTATION_ERRORS, APIFY_ROTATION_HTTP_CODES, MAX_RETRIES
from utils.logger import get_logger

logger = get_logger()


class ApifyService:

    def __init__(self, rotator: KeyRotator):
        self.rotator = rotator

    def _client(self) -> ApifyClient:
        return ApifyClient(self.rotator.get_current_key())

    def run_actor(self, actor_id: str, run_input: dict) -> dict:
        """Run an Apify actor with automatic key rotation on quota errors."""
        for attempt in range(MAX_RETRIES):
            try:
                return self._client().actor(actor_id).call(run_input=run_input)
            except Exception as e:
                err = str(e).lower()
                if any(p in err for p in APIFY_ROTATION_ERRORS):
                    try:
                        old = self.rotator.get_current_key()
                        self.rotator.mark_key_failed(old, err[:60])
                        logger.warning(f"Apify key rotated. Attempt {attempt + 1}/{MAX_RETRIES}")
                    except AllKeysExhaustedException:
                        raise
                else:
                    raise
        raise RuntimeError("Max Apify retry attempts reached")

    def get_dataset(self, dataset_id: str) -> list:
        """Iterate all items from an Apify dataset."""
        return list(self._client().dataset(dataset_id).iterate_items())

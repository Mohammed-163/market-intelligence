import sys
from pathlib import Path
from loguru import logger
from config.constants import LOG_FILE

# Ensure log directory exists before configuring file handler
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(LOG_FILE, rotation="10 MB", retention="10 days", level="DEBUG")

def get_logger():
    return logger

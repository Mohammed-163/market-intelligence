import sys
from loguru import logger
from config.constants import LOG_FILE

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(LOG_FILE, rotation="10 MB", retention="10 days", level="DEBUG")

def get_logger():
    return logger

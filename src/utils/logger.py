import os
from loguru import logger
from utils.config import config

os.makedirs("logs", exist_ok=True)

logger.remove()

logger.add(
    f"logs/{config.log.file}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {file.path}:{line} - {message}",
    rotation="10 MB",
    compression="zip",
    enqueue=True,  # Make logging thread-safe
    backtrace=True,  # Include full traceback on errors
    diagnose=True  # Include variable values in tracebacks
)

# Add console handler
logger.add(
    sink=lambda msg: print(msg, end=""),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> - <level>{level}</level> - {file.path}:{line} - <level>{message}</level>",
    enqueue=True,  # Make logging thread-safe
    backtrace=True,  # Include full traceback on errors
    diagnose=True  # Include variable values in tracebacks
)

# Example usage
if __name__ == "__main__":

    logger.info("Application started")
    logger.warning("This is a test warning")
    logger.error("This is a test error")

    try:
        x = 1 / 0
    except Exception:
        logger.exception("Something went wrong")

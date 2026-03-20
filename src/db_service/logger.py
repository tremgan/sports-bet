import logging
from rich.logging import RichHandler
from pathlib import Path

LOG_FILE = Path(__file__).parent / "main.log"


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("db_service")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

        rich_handler = RichHandler(rich_tracebacks=True)
        rich_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(rich_handler)

    return logger

logger = setup_logger()

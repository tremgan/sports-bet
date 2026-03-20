import logging
import sys
from rich.logging import RichHandler
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "main.log"),
        RichHandler(rich_tracebacks=True),
    ],
)

logger = logging.getLogger("db_service")

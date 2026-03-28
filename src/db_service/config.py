from dotenv import load_dotenv
import os
from sqlmodel import create_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv(override=False)  # reads .env from cwd by default

SQLMODEL_DB_URL = os.getenv("SQLMODEL_DB_URL")

if not SQLMODEL_DB_URL:
    logger.warning(
        "SQLMODEL_DB_URL is not set. Database operations will fail until it is configured."
    )

engine = create_engine(SQLMODEL_DB_URL) if SQLMODEL_DB_URL else None

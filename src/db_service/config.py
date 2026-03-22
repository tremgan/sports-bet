from dotenv import load_dotenv
import os
from sqlmodel import create_engine

load_dotenv()  # reads .env from cwd by default

SQLMODEL_DB_URL = os.getenv("SQLMODEL_DB_URL", False)
if not SQLMODEL_DB_URL:
    raise ValueError("SQLMODEL_DB_URL environment variable is not set.")


engine = create_engine(SQLMODEL_DB_URL, echo=True)

from dotenv import load_dotenv
import os

load_dotenv()

DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://127.0.0.1:8000")
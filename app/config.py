from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-generate-a-fernet-key")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "uptime-status.db"))
CACHE_INTERVAL = int(os.getenv("CACHE_INTERVAL", "10"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "80"))

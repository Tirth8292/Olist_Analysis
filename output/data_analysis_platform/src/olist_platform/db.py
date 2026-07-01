import sqlite3
from pathlib import Path
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

from .config import WAREHOUSE_PATH

# Load environment variables from .env file
load_dotenv()


def connect():
    # Check if DATABASE_URL is set (for PostgreSQL)
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # PostgreSQL connection (production)
        conn = psycopg2.connect(database_url, cursor_factory=DictCursor)
        return conn
    else:
        # SQLite connection (local development)
        path = WAREHOUSE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

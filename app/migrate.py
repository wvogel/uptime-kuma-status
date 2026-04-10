import logging
from sqlalchemy import text, inspect
from app.database import engine

log = logging.getLogger(__name__)

COLUMN_MIGRATIONS = [
    ("incident", "occurred_at", "ALTER TABLE incident ADD COLUMN occurred_at TEXT NOT NULL DEFAULT ''"),
    ("incident", "position", "ALTER TABLE incident ADD COLUMN position INTEGER NOT NULL DEFAULT 0"),
    ("incident", "resolved_at", "ALTER TABLE incident ADD COLUMN resolved_at TEXT DEFAULT NULL"),
]


def run_migrations():
    insp = inspect(engine)
    tables = insp.get_table_names()

    with engine.begin() as conn:
        # Migrate kuma_instance from DB-credentials to API-based
        if "kuma_instance" in tables:
            columns = [c["name"] for c in insp.get_columns("kuma_instance")]
            if "host" in columns and "api_url" not in columns:
                log.info("Migration: recreating kuma_instance (DB credentials -> API)")
                conn.execute(text("DROP TABLE IF EXISTS hidden_monitor"))
                conn.execute(text("DROP TABLE IF EXISTS kuma_instance"))

        # Column additions
        insp = inspect(engine)  # refresh after potential drops
        for table, column, sql in COLUMN_MIGRATIONS:
            if table not in insp.get_table_names():
                continue
            columns = [c["name"] for c in insp.get_columns(table)]
            if column not in columns:
                log.info("Migration: adding column %s.%s", table, column)
                conn.execute(text(sql))

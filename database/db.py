import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_NAME = "productivityguard.db"

DEFAULT_PRODUCTIVE_SITES = [
    "coursera.org",
    "udemy.com",
    "almalearn.com",
    "github.com",
    "stackoverflow.com",
    "docs.python.org",
    "developer.mozilla.org",
    "w3schools.com",
    "leetcode.com",
    "geeksforgeeks.org",
]

DEFAULT_TIMEPASS_SITES = [
    "instagram.com",
    "youtube.com",
    "facebook.com",
    "reddit.com",
    "netflix.com",
    "hotstar.com",
    "primevideo.com",
]

DEFAULT_SETTINGS = {
    "earn_ratio_productive_minutes": "6",
    "daily_bonus_goal_minutes": "240",
    "daily_bonus_minutes": "20",
    "idle_timeout_seconds": "300",
    "carryover_cap_minutes": "120",
    "heartbeat_interval_seconds": "15",
}

DEFAULT_TASKS = [
    "Sleep for 7 hrs",
    "Workout",
    "5hr of study",
    "5 Python Q's",
    "5 SQL Q's",
    "Communication practice",
    "Skin Care",
    "Sleep at 11:30",
]


def get_database_path():
    return os.environ.get("PRODUCTIVITYGUARD_DB", str(BASE_DIR / DB_NAME))


def get_connection():
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid


def fetch_all(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def _run_migrations(cursor):
    if not _column_exists(cursor, "coins", "balance_seconds"):
        cursor.execute("ALTER TABLE coins ADD COLUMN balance_seconds REAL NOT NULL DEFAULT 0")


def _seed_defaults(cursor):
    cursor.execute("INSERT OR IGNORE INTO coins (id, balance, balance_seconds) VALUES (1, 0, 0)")

    for key, value in DEFAULT_SETTINGS.items():
        cursor.execute(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    cursor.execute("SELECT COUNT(*) AS total FROM site_rules")
    if cursor.fetchone()["total"] == 0:
        for domain in DEFAULT_PRODUCTIVE_SITES:
            cursor.execute(
                "INSERT INTO site_rules (domain, category) VALUES (?, 'productive')",
                (domain,),
            )

        for domain in DEFAULT_TIMEPASS_SITES:
            cursor.execute(
                "INSERT INTO site_rules (domain, category) VALUES (?, 'timepass')",
                (domain,),
            )

    cursor.execute("SELECT COUNT(*) AS total FROM task_templates")
    if cursor.fetchone()["total"] == 0:
        for index, title in enumerate(DEFAULT_TASKS, start=1):
            cursor.execute(
                "INSERT INTO task_templates (title, sort_order, active) VALUES (?, ?, 1)",
                (title, index),
            )


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    schema_path = BASE_DIR / "database" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    cursor.executescript(schema)
    _run_migrations(cursor)
    _seed_defaults(cursor)

    conn.commit()
    conn.close()

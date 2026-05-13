CREATE TABLE IF NOT EXISTS coins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    balance INTEGER NOT NULL DEFAULT 0,
    balance_seconds REAL NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_name TEXT,
    category TEXT,  -- "productive" or "timepass"
    start_time TEXT,
    end_time TEXT,
    duration_minutes INTEGER
);


CREATE TABLE IF NOT EXISTS site_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK(category IN ('productive', 'timepass'))
);


CREATE TABLE IF NOT EXISTS activity_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    domain TEXT,
    title TEXT,
    category TEXT NOT NULL CHECK(category IN ('productive', 'timepass', 'neutral')),
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    counted INTEGER NOT NULL DEFAULT 1
);


CREATE TABLE IF NOT EXISTS daily_bonus (
    bonus_date TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    bonus_seconds REAL NOT NULL
);


CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

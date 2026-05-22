from datetime import datetime, timedelta
from urllib.parse import urlparse

from database.db import execute_query, fetch_all, fetch_one, initialize_database


LAST_HEARTBEAT_KEYS = (
    "last_url",
    "last_domain",
    "last_title",
    "last_category",
    "last_observed_at",
    "last_idle",
)


def local_now():
    return datetime.now().replace(microsecond=0)


def utc_now():
    return local_now()


def parse_timestamp(value):
    if not value:
        return local_now()
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def iso(value):
    return value.replace(microsecond=0).isoformat()


def normalize_domain(domain_or_url):
    value = (domain_or_url or "").strip().lower()
    if not value:
        return ""
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.hostname or ""
    value = value.split("/")[0].split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    return value


def get_setting(key, default=None):
    row = fetch_one("SELECT value FROM app_settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key, value):
    execute_query(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def get_int_setting(key, default):
    try:
        return int(float(get_setting(key, default)))
    except (TypeError, ValueError):
        return int(default)


def get_settings():
    rows = fetch_all("SELECT key, value FROM app_settings ORDER BY key")
    settings = {row["key"]: row["value"] for row in rows}
    return {
        **settings,
        "earn_ratio_productive_minutes": get_int_setting("earn_ratio_productive_minutes", 6),
        "daily_bonus_goal_minutes": get_int_setting("daily_bonus_goal_minutes", 240),
        "daily_bonus_minutes": get_int_setting("daily_bonus_minutes", 20),
        "idle_timeout_seconds": get_int_setting("idle_timeout_seconds", 300),
        "carryover_cap_minutes": get_int_setting("carryover_cap_minutes", 120),
        "heartbeat_interval_seconds": get_int_setting("heartbeat_interval_seconds", 15),
    }


def update_settings(payload):
    allowed = {
        "earn_ratio_productive_minutes",
        "daily_bonus_goal_minutes",
        "daily_bonus_minutes",
        "idle_timeout_seconds",
        "carryover_cap_minutes",
        "heartbeat_interval_seconds",
    }
    for key, value in payload.items():
        if key in allowed:
            set_setting(key, max(1, int(value)))
    cap_balance()
    return get_settings()


def get_balance_seconds():
    row = fetch_one("SELECT balance_seconds FROM coins WHERE id = 1")
    return float(row["balance_seconds"]) if row else 0.0


def set_balance_seconds(value):
    capped = max(0.0, min(float(value), get_int_setting("carryover_cap_minutes", 120) * 60.0))
    execute_query(
        "UPDATE coins SET balance_seconds = ?, balance = ? WHERE id = 1",
        (capped, int(capped // 60)),
    )
    return capped


def cap_balance():
    return set_balance_seconds(get_balance_seconds())


def change_balance(delta_seconds):
    return set_balance_seconds(get_balance_seconds() + float(delta_seconds))


def list_rules():
    rows = fetch_all("SELECT domain, category FROM site_rules ORDER BY category, domain")
    return {
        "productive": [row["domain"] for row in rows if row["category"] == "productive"],
        "timepass": [row["domain"] for row in rows if row["category"] == "timepass"],
    }


def replace_rules(payload):
    productive = payload.get("productive", [])
    timepass = payload.get("timepass", [])
    execute_query("DELETE FROM site_rules")
    for category, domains in (("productive", productive), ("timepass", timepass)):
        for domain in domains:
            normalized = normalize_domain(domain)
            if normalized:
                execute_query(
                    "INSERT OR REPLACE INTO site_rules (domain, category) VALUES (?, ?)",
                    (normalized, category),
                )
    return list_rules()


def add_rule(domain, category):
    normalized = normalize_domain(domain)
    if category not in {"productive", "timepass"} or not normalized:
        raise ValueError("Rules need a valid domain and category.")
    execute_query(
        "INSERT OR REPLACE INTO site_rules (domain, category) VALUES (?, ?)",
        (normalized, category),
    )
    return list_rules()


def delete_rule(domain):
    execute_query("DELETE FROM site_rules WHERE domain = ?", (normalize_domain(domain),))
    return list_rules()


def classify_domain(domain):
    normalized = normalize_domain(domain)
    if not normalized:
        return "neutral"
    rows = fetch_all("SELECT domain, category FROM site_rules")
    best_match = None
    for row in rows:
        rule_domain = row["domain"]
        if normalized == rule_domain or normalized.endswith("." + rule_domain):
            if best_match is None or len(rule_domain) > len(best_match["domain"]):
                best_match = row
    return best_match["category"] if best_match else "neutral"


def record_session(previous, ended_at, duration_seconds):
    if duration_seconds <= 0:
        return

    execute_query(
        "INSERT INTO activity_sessions "
        "(url, domain, title, category, started_at, ended_at, duration_seconds, counted) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        (
            previous.get("url"),
            previous.get("domain"),
            previous.get("title"),
            previous.get("category", "neutral"),
            previous.get("observed_at"),
            iso(ended_at),
            duration_seconds,
        ),
    )

    category = previous.get("category")
    if category == "productive":
        ratio = get_int_setting("earn_ratio_productive_minutes", 6)
        change_balance(duration_seconds / ratio)
    elif category == "timepass":
        change_balance(-duration_seconds)


def today_totals(now=None):
    now = now or local_now()
    today_prefix = now.date().isoformat()
    rows = fetch_all(
        "SELECT category, COALESCE(SUM(duration_seconds), 0) AS seconds "
        "FROM activity_sessions WHERE DATE(started_at) = ? GROUP BY category",
        (today_prefix,),
    )
    totals = {"productive": 0.0, "timepass": 0.0, "neutral": 0.0}
    for row in rows:
        totals[row["category"]] = float(row["seconds"])
    return totals


def maybe_apply_daily_bonus(now=None):
    now = now or local_now()
    today = now.date().isoformat()
    already_applied = fetch_one("SELECT bonus_date FROM daily_bonus WHERE bonus_date = ?", (today,))
    if already_applied:
        return False

    goal_seconds = get_int_setting("daily_bonus_goal_minutes", 240) * 60
    bonus_seconds = get_int_setting("daily_bonus_minutes", 20) * 60
    if today_totals(now)["productive"] >= goal_seconds:
        execute_query(
            "INSERT INTO daily_bonus (bonus_date, applied_at, bonus_seconds) VALUES (?, ?, ?)",
            (today, iso(now), bonus_seconds),
        )
        change_balance(bonus_seconds)
        return True
    return False


def get_previous_heartbeat():
    values = {key: get_setting(key) for key in LAST_HEARTBEAT_KEYS}
    if not values.get("last_observed_at"):
        return None
    return {
        "url": values.get("last_url"),
        "domain": values.get("last_domain"),
        "title": values.get("last_title"),
        "category": values.get("last_category") or "neutral",
        "observed_at": values.get("last_observed_at"),
        "idle": values.get("last_idle") == "1",
    }


def save_current_heartbeat(url, domain, title, category, observed_at, idle):
    values = {
        "last_url": url or "",
        "last_domain": domain or "",
        "last_title": title or "",
        "last_category": category or "neutral",
        "last_observed_at": iso(observed_at),
        "last_idle": "1" if idle else "0",
    }
    for key, value in values.items():
        set_setting(key, value)


def handle_heartbeat(payload):
    initialize_database()

    observed_at = parse_timestamp(payload.get("timestamp"))
    url = payload.get("url") or ""
    domain = normalize_domain(payload.get("domain") or url)
    title = payload.get("title") or ""
    idle = bool(payload.get("idle"))
    category = classify_domain(domain)

    previous = get_previous_heartbeat()
    if previous:
        previous_at = parse_timestamp(previous["observed_at"])
        elapsed = (observed_at - previous_at).total_seconds()
        max_gap = get_int_setting("idle_timeout_seconds", 300) + 30
        if not previous.get("idle") and 0 < elapsed <= max_gap:
            record_session(previous, observed_at, elapsed)

    maybe_apply_daily_bonus(observed_at)
    save_current_heartbeat(url, domain, title, category, observed_at, idle)

    balance_seconds = get_balance_seconds()
    blocked = category == "timepass" and balance_seconds <= 0
    return {
        "ok": True,
        "blocked": blocked,
        "category": category,
        "domain": domain,
        "balance_seconds": balance_seconds,
        "balance_minutes": round(balance_seconds / 60, 1),
        "state": get_state(observed_at),
    }


def get_state(now=None):
    initialize_database()
    now = now or local_now()
    totals = today_totals(now)
    balance_seconds = get_balance_seconds()
    last = get_previous_heartbeat()
    last_category = last["category"] if last else "neutral"
    return {
        "balance_seconds": balance_seconds,
        "balance_minutes": round(balance_seconds / 60, 1),
        "today": {
            "productive_minutes": round(totals["productive"] / 60, 1),
            "timepass_minutes": round(totals["timepass"] / 60, 1),
            "neutral_minutes": round(totals["neutral"] / 60, 1),
        },
        "active": last,
        "active_category": last_category,
        "rules": list_rules(),
        "settings": get_settings(),
    }


def date_range(days, now=None):
    now = now or local_now()
    start = now.date() - timedelta(days=days - 1)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def week_dates(now=None):
    return date_range(7, now)


def get_range_analytics(days, now=None):
    initialize_database()
    dates = date_range(days, now)
    rows = fetch_all(
        "SELECT DATE(started_at) AS activity_date, category, "
        "COALESCE(SUM(duration_seconds), 0) AS seconds "
        "FROM activity_sessions "
        "WHERE DATE(started_at) BETWEEN ? AND ? "
        "GROUP BY DATE(started_at), category",
        (dates[0], dates[-1]),
    )

    buckets = {
        date: {
            "date": date,
            "productive_hours": 0.0,
            "timepass_hours": 0.0,
            "neutral_hours": 0.0,
        }
        for date in dates
    }
    totals = {"productive_hours": 0.0, "timepass_hours": 0.0, "neutral_hours": 0.0}

    for row in rows:
        key = f"{row['category']}_hours"
        hours = round(float(row["seconds"]) / 3600, 2)
        if row["activity_date"] in buckets and key in buckets[row["activity_date"]]:
            buckets[row["activity_date"]][key] = hours

    for bucket in buckets.values():
        for key in totals:
            totals[key] += bucket[key]

    return {
        "days": list(buckets.values()),
        "totals": {key: round(value, 2) for key, value in totals.items()},
    }


def get_weekly_analytics(now=None):
    return get_range_analytics(7, now)


def get_monthly_analytics(now=None):
    return get_range_analytics(30, now)


def get_task_templates():
    return fetch_all(
        "SELECT id, title, sort_order FROM task_templates "
        "WHERE active = 1 ORDER BY sort_order, id"
    )


def get_today_tasks(now=None):
    initialize_database()
    now = now or local_now()
    task_date = now.date().isoformat()
    tasks = []

    for task in get_task_templates():
        completion = fetch_one(
            "SELECT completed FROM task_completions WHERE task_date = ? AND task_id = ?",
            (task_date, task["id"]),
        )
        tasks.append(
            {
                "id": task["id"],
                "title": task["title"],
                "completed": bool(completion and completion["completed"]),
            }
        )

    completed_count = sum(1 for task in tasks if task["completed"])
    total_count = len(tasks)
    return {
        "date": task_date,
        "tasks": tasks,
        "completed_count": completed_count,
        "total_count": total_count,
        "completion_percent": round((completed_count / total_count) * 100, 1) if total_count else 0,
    }


def update_today_task(payload, now=None):
    initialize_database()
    now = now or local_now()
    task_date = now.date().isoformat()
    task_id = int(payload.get("task_id", 0))
    completed = 1 if payload.get("completed") else 0

    task = fetch_one("SELECT id FROM task_templates WHERE id = ? AND active = 1", (task_id,))
    if not task:
        raise ValueError("Unknown task.")

    execute_query(
        "INSERT INTO task_completions (task_date, task_id, completed, updated_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(task_date, task_id) DO UPDATE SET "
        "completed = excluded.completed, updated_at = excluded.updated_at",
        (task_date, task_id, completed, iso(now)),
    )
    return get_today_tasks(now)


def get_task_summary(now=None):
    initialize_database()
    dates = week_dates(now)
    templates = get_task_templates()
    total_tasks = len(templates)
    rows = fetch_all(
        "SELECT task_date, COALESCE(SUM(completed), 0) AS completed_count "
        "FROM task_completions WHERE task_date BETWEEN ? AND ? GROUP BY task_date",
        (dates[0], dates[-1]),
    )
    completed_by_date = {row["task_date"]: int(row["completed_count"]) for row in rows}

    days = []
    for date in dates:
        completed_count = completed_by_date.get(date, 0)
        days.append(
            {
                "date": date,
                "completed_count": completed_count,
                "total_count": total_tasks,
                "completion_percent": round((completed_count / total_tasks) * 100, 1)
                if total_tasks
                else 0,
            }
        )

    best_day = max(days, key=lambda day: (day["completion_percent"], day["completed_count"]))
    today = days[-1]
    weekly_completed = sum(day["completed_count"] for day in days)
    weekly_total = total_tasks * len(days)

    return {
        "days": days,
        "today": today,
        "best_day": best_day,
        "weekly_completion_percent": round((weekly_completed / weekly_total) * 100, 1)
        if weekly_total
        else 0,
    }

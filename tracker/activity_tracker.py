from database.db import execute_query, fetch_all
from datetime import datetime


def log_activity(activity_name, category, start_time, end_time, duration):
    execute_query(
        "INSERT INTO activity_logs (activity_name, category, start_time, end_time, duration_minutes) VALUES (?, ?, ?, ?, ?)",
        (activity_name, category, start_time, end_time, duration)
    )

def get_today_activity():
    today = datetime.now().strftime("%Y-%m-%d")

    return fetch_all(
        "SELECT * FROM activity_logs WHERE DATE(start_time) = ?",
        (today,)
    )

def get_today_category_minutes(category):
    result = fetch_all(
        "SELECT SUM(duration_minutes) FROM activity_logs WHERE DATE(start_time) = DATE('now') AND category = ?",
        (category,)
    )

    return result[0]["SUM(duration_minutes)"] if result and result[0]["SUM(duration_minutes)"] else 0



if __name__ == "__main__":
    from database.db import initialize_database
    from datetime import datetime

    # 🔥 THIS LINE IS MISSING IN YOUR FLOW
    initialize_database()

    start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end = start

    log_activity("YouTube", "timepass", start, end, 10)

    print(get_today_activity())
    print(get_today_category_minutes("timepass"))

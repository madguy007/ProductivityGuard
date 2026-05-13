from database.db import fetch_all, execute_query
from services.productivity import get_balance_seconds, handle_heartbeat
from tracker.activity_tracker import get_today_category_minutes


def calculate_coins(minutes):
    return int(minutes / 6)


def get_balance():
    return int(get_balance_seconds() // 60)


def initialize_balance():
    result = fetch_all("SELECT * FROM coins WHERE id = 1")

    if not result:
        execute_query("INSERT INTO coins (id, balance) VALUES (1, 0)")


def add_coins(coins):
    current_balance = get_balance()
    new_balance = current_balance + coins

    execute_query(
        "UPDATE coins SET balance = ?, balance_seconds = ? WHERE id = 1",
        (new_balance, new_balance * 60)
    )


def update_coins_from_activity():
    productive = get_today_category_minutes("productive")
    timepass = get_today_category_minutes("timepass")

    net_minutes = (productive / 6) - timepass

    coins = max(0, net_minutes)

    execute_query("UPDATE coins SET balance = ?, balance_seconds = ? WHERE id = 1", (int(coins), coins * 60))


if __name__ == "__main__":
    from database.db import initialize_database

    initialize_database()

    update_coins_from_activity()
    print(get_balance())

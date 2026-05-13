from coin_engine.coins import get_balance


def can_do_timepass():
    return get_balance() > 0

def check_timepass_permission(activity_name):
    if can_do_timepass():
        print(f"✅ Allowed to use {activity_name}")
        return True
    else:
        print(f"❌ Blocked! No coins left for {activity_name}")
        return False
    
if __name__ == "__main__":
    from database.db import initialize_database

    initialize_database()

    print(check_timepass_permission("YouTube"))
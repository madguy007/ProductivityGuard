import os
import tempfile
import unittest

from database.db import initialize_database
from database.db import execute_query
from services.productivity import (
    change_balance,
    classify_domain,
    get_task_summary,
    get_today_tasks,
    get_balance_seconds,
    get_state,
    get_monthly_analytics,
    get_weekly_analytics,
    handle_heartbeat,
    parse_timestamp,
    set_setting,
    update_today_task,
)


class ProductivityRulesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.NamedTemporaryFile(delete=False)
        self.temp.close()
        os.environ["PRODUCTIVITYGUARD_DB"] = self.temp.name
        initialize_database()

    def tearDown(self):
        os.environ.pop("PRODUCTIVITYGUARD_DB", None)
        os.unlink(self.temp.name)

    def heartbeat(self, url, timestamp, idle=False):
        return handle_heartbeat(
            {
                "url": url,
                "domain": url,
                "title": "Test",
                "idle": idle,
                "timestamp": timestamp,
            }
        )

    def test_default_domain_classification(self):
        self.assertEqual(classify_domain("github.com"), "productive")
        self.assertEqual(classify_domain("www.youtube.com"), "timepass")
        self.assertEqual(classify_domain("example.com"), "neutral")

    def test_deleted_default_rule_is_not_reseeded(self):
        execute_query("DELETE FROM site_rules WHERE domain = ?", ("youtube.com",))
        initialize_database()

        self.assertEqual(classify_domain("youtube.com"), "neutral")

    def test_productive_time_earns_timepass_minutes(self):
        self.heartbeat("https://github.com", "2026-05-13T10:00:00")
        self.heartbeat("https://github.com", "2026-05-13T10:03:00")
        self.heartbeat("https://github.com", "2026-05-13T10:06:00")

        self.assertEqual(round(get_balance_seconds()), 60)
        self.assertEqual(get_state(parse_timestamp("2026-05-13T10:06:00"))["today"]["productive_minutes"], 6.0)

    def test_timepass_consumes_balance_and_blocks_at_zero(self):
        change_balance(60)

        self.heartbeat("https://youtube.com", "2026-05-13T10:00:00")
        result = self.heartbeat("https://youtube.com", "2026-05-13T10:01:00")

        self.assertEqual(round(get_balance_seconds()), 0)
        self.assertTrue(result["blocked"])

    def test_idle_time_is_not_counted(self):
        self.heartbeat("https://github.com", "2026-05-13T10:00:00", idle=True)
        self.heartbeat("https://github.com", "2026-05-13T10:06:00")

        self.assertEqual(round(get_balance_seconds()), 0)
        self.assertEqual(get_state()["today"]["productive_minutes"], 0.0)

    def test_daily_bonus_applies_once_after_goal(self):
        set_setting("idle_timeout_seconds", 20000)

        self.heartbeat("https://github.com", "2026-05-13T10:00:00")
        self.heartbeat("https://github.com", "2026-05-13T14:00:00")
        first_balance = round(get_balance_seconds())
        self.heartbeat("https://github.com", "2026-05-13T14:01:00")

        self.assertEqual(first_balance, 3600)
        self.assertEqual(round(get_balance_seconds()), 3610)

    def test_carryover_cap_is_enforced(self):
        change_balance(200 * 60)

        self.assertEqual(round(get_balance_seconds()), 120 * 60)

    def test_weekly_analytics_returns_seven_days_with_zero_buckets(self):
        set_setting("idle_timeout_seconds", 4000)
        self.heartbeat("https://github.com", "2026-05-13T10:00:00")
        self.heartbeat("https://github.com", "2026-05-13T11:00:00")

        analytics = get_weekly_analytics(parse_timestamp("2026-05-15T09:00:00"))

        self.assertEqual(len(analytics["days"]), 7)
        self.assertEqual(analytics["days"][0]["date"], "2026-05-09")
        self.assertEqual(analytics["days"][-1]["date"], "2026-05-15")
        may_13 = [day for day in analytics["days"] if day["date"] == "2026-05-13"][0]
        self.assertEqual(may_13["productive_hours"], 1.0)
        self.assertEqual(analytics["totals"]["productive_hours"], 1.0)

    def test_monthly_analytics_returns_thirty_days(self):
        set_setting("idle_timeout_seconds", 8000)
        self.heartbeat("https://github.com", "2026-05-01T10:00:00")
        self.heartbeat("https://github.com", "2026-05-01T12:00:00")

        analytics = get_monthly_analytics(parse_timestamp("2026-05-30T09:00:00"))

        self.assertEqual(len(analytics["days"]), 30)
        self.assertEqual(analytics["days"][0]["date"], "2026-05-01")
        self.assertEqual(analytics["days"][-1]["date"], "2026-05-30")
        may_1 = [day for day in analytics["days"] if day["date"] == "2026-05-01"][0]
        self.assertEqual(may_1["productive_hours"], 2.0)
        self.assertEqual(analytics["totals"]["productive_hours"], 2.0)

    def test_default_tasks_seed_once(self):
        initialize_database()
        tasks = get_today_tasks(parse_timestamp("2026-05-13T10:00:00"))["tasks"]

        self.assertEqual(len(tasks), 8)
        self.assertEqual(tasks[0]["title"], "Sleep for 7 hrs")

    def test_task_completion_is_scoped_to_today(self):
        today = parse_timestamp("2026-05-13T10:00:00")
        tomorrow = parse_timestamp("2026-05-14T10:00:00")
        task_id = get_today_tasks(today)["tasks"][0]["id"]

        update_today_task({"task_id": task_id, "completed": True}, today)

        self.assertEqual(get_today_tasks(today)["completed_count"], 1)
        self.assertEqual(get_today_tasks(tomorrow)["completed_count"], 0)

    def test_task_summary_reports_best_day_and_weekly_percent(self):
        day_one = parse_timestamp("2026-05-13T10:00:00")
        day_two = parse_timestamp("2026-05-14T10:00:00")
        tasks = get_today_tasks(day_one)["tasks"]

        update_today_task({"task_id": tasks[0]["id"], "completed": True}, day_one)
        update_today_task({"task_id": tasks[1]["id"], "completed": True}, day_two)
        update_today_task({"task_id": tasks[2]["id"], "completed": True}, day_two)

        summary = get_task_summary(day_two)

        self.assertEqual(summary["best_day"]["date"], "2026-05-14")
        self.assertEqual(summary["today"]["completed_count"], 2)
        self.assertEqual(summary["weekly_completion_percent"], 5.4)


if __name__ == "__main__":
    unittest.main()

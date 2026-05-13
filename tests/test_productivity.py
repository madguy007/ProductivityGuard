import os
import tempfile
import unittest

from database.db import initialize_database
from services.productivity import (
    change_balance,
    classify_domain,
    get_balance_seconds,
    get_state,
    handle_heartbeat,
    set_setting,
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

    def test_productive_time_earns_timepass_minutes(self):
        self.heartbeat("https://github.com", "2026-05-13T10:00:00")
        self.heartbeat("https://github.com", "2026-05-13T10:03:00")
        self.heartbeat("https://github.com", "2026-05-13T10:06:00")

        self.assertEqual(round(get_balance_seconds()), 60)
        self.assertEqual(get_state()["today"]["productive_minutes"], 6.0)

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


if __name__ == "__main__":
    unittest.main()

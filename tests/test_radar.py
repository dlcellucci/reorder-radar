"""Checks that Reorder Radar labels accounts the way the rules say.

Run with:  python -m unittest discover tests
"""
import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import radar  # noqa: E402

AS_OF = date(2026, 11, 2)


def orders_every(gap, last_days_ago, count):
    """Make a list of order dates, `gap` days apart, the last one `last_days_ago` before AS_OF."""
    last = AS_OF - timedelta(days=last_days_ago)
    return [last - timedelta(days=gap * i) for i in range(count)]


def status_of(dates):
    return radar.score_account(dates, [1000] * len(dates), AS_OF)["status"]


class RuleTests(unittest.TestCase):
    def test_on_track(self):
        self.assertEqual(status_of(orders_every(14, 10, 5)), "On track")

    def test_due_now_on_the_day(self):
        self.assertEqual(status_of(orders_every(14, 14, 5)), "Due now")

    def test_due_now_at_grace_edge(self):
        self.assertEqual(status_of(orders_every(14, 21, 5)), "Due now")  # exactly 7 late

    def test_overdue_one_day_past_grace(self):
        self.assertEqual(status_of(orders_every(14, 22, 5)), "Overdue")  # 8 late

    def test_lapsed_after_120_days(self):
        self.assertEqual(status_of(orders_every(30, 140, 5)), "Lapsed")

    def test_lapsed_uses_3x_gap_when_longer(self):
        # orders every 60 days: 3x = 180 beats 120, so 150 days is overdue, not lapsed
        self.assertEqual(status_of(orders_every(60, 150, 4)), "Overdue")
        self.assertEqual(status_of(orders_every(60, 180, 4)), "Lapsed")

    def test_one_order_is_new(self):
        self.assertEqual(status_of(orders_every(0, 12, 1)), "New")

    def test_one_order_long_ago_is_lapsed(self):
        self.assertEqual(status_of(orders_every(0, 130, 1)), "Lapsed")

    def test_same_day_orders_count_once(self):
        d = orders_every(14, 10, 3)
        r = radar.score_account(d + [d[0]], [500] * 4, AS_OF)
        self.assertEqual(r["orders"], 3)
        self.assertEqual(r["usual_gap"], 14)


class SampleDataTests(unittest.TestCase):
    """The sample file was built so each status shows up. If these fail, the rules changed."""

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "..", "data", "orders.csv")
        dates, totals = radar.load_orders(path)
        self._ranked = radar.run_radar(dates, totals, AS_OF)
        self.rows = {r["account"]: r for r in self._ranked}

    def test_expected_statuses(self):
        expected = {
            "Blue Ridge Grocers": "Lapsed",
            "Old Mill Mercantile": "Overdue",
            "Riverbend Supply": "Overdue",
            "Harbor Light Co-op": "Overdue",
            "North Fork Provisions": "Due now",
            "Summit Farm Stand": "New",
            "Pine Hollow Market": "On track",
            "Cedar Street Shop": "On track",
        }
        self.assertEqual({k: v["status"] for k, v in self.rows.items()}, expected)

    def test_overdue_ranked_by_order_size(self):
        overdue = [r["account"] for r in self._ranked if r["status"] == "Overdue"]
        self.assertEqual(overdue, ["Harbor Light Co-op", "Old Mill Mercantile", "Riverbend Supply"])

    def test_sample_has_48_orders(self):
        self.assertEqual(sum(r["orders"] for r in self.rows.values()), 48)


if __name__ == "__main__":
    unittest.main()

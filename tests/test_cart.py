"""Checks that Reorder Cart picks the right accounts and builds sane carts.

Run with:  python -m unittest discover tests
"""
import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import cart  # noqa: E402

AS_OF = date(2026, 11, 16)
HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")


def account(gap, last_days_ago, count=4, product="Kenya AA - 12oz Bag", qty=20, status="delivered"):
    last = AS_OF - timedelta(days=last_days_ago)
    return [{"date": last - timedelta(days=gap * i), "status": status,
             "lines": [{"product": product, "category": "Retail Bag", "qty": qty, "price": 10}]}
            for i in range(count)]


def stock(**qty):
    names = {"kenya": "Kenya AA - 12oz Bag", "guji": "Ethiopia Guji - 12oz Bag", "decaf": "Decaf - 2lb Bag"}
    return {names[k]: {"qty": v, "price": 10, "category": "Retail Bag"} for k, v in qty.items()}


class WindowTests(unittest.TestCase):
    def test_due_today_is_in(self):
        self.assertIsNotNone(cart.build_cart(account(14, 14), stock(kenya=100), AS_OF))

    def test_three_days_early_is_in(self):
        self.assertIsNotNone(cart.build_cart(account(14, 11), stock(kenya=100), AS_OF))

    def test_four_days_early_is_out(self):
        self.assertIsNone(cart.build_cart(account(14, 10), stock(kenya=100), AS_OF))

    def test_two_days_late_is_in(self):
        self.assertIsNotNone(cart.build_cart(account(14, 16), stock(kenya=100), AS_OF))

    def test_three_days_late_is_out(self):
        self.assertIsNone(cart.build_cart(account(14, 17), stock(kenya=100), AS_OF))

    def test_needs_three_orders(self):
        self.assertIsNone(cart.build_cart(account(14, 14, count=2), stock(kenya=100), AS_OF))

    def test_open_order_skips_account(self):
        orders = account(14, 14)
        orders.append({"date": AS_OF, "status": "open", "lines": orders[0]["lines"]})
        self.assertIsNone(cart.build_cart(orders, stock(kenya=100), AS_OF))


class CartTests(unittest.TestCase):
    def test_usual_quantity(self):
        r = cart.build_cart(account(14, 14, qty=20), stock(kenya=100), AS_OF)
        self.assertEqual(sum(c["qty"] for c in r["cart"]), 20)

    def test_swaps_variety_when_theirs_is_gone(self):
        r = cart.build_cart(account(14, 14), stock(guji=100), AS_OF)
        self.assertEqual(r["cart"][0]["product"], "Ethiopia Guji - 12oz Bag")
        self.assertEqual(r["cart"][0]["note"], "different variety, same type")

    def test_never_promises_more_than_stock(self):
        r = cart.build_cart(account(14, 14, qty=50), stock(kenya=10, guji=5), AS_OF)
        self.assertEqual(sum(c["qty"] for c in r["cart"]), 15)
        self.assertTrue(any(f.startswith("Short 35") for f in r["flags"]))

    def test_holds_stock_between_accounts(self):
        inv = stock(kenya=25)
        cart.build_cart(account(14, 14, qty=20), inv, AS_OF)
        second = cart.build_cart(account(14, 14, qty=20), inv, AS_OF)
        self.assertEqual(sum(c["qty"] for c in second["cart"]), 5)

    def test_try_new_is_something_they_never_bought(self):
        r = cart.build_cart(account(14, 14), stock(kenya=100, decaf=30), AS_OF)
        self.assertEqual(r["try_new"], ["Decaf - 2lb Bag"])

    def test_product_type_ignores_variety(self):
        self.assertEqual(cart.product_type("Kenya AA - 12oz Bag"), cart.product_type("House - 12oz Bag"))


class SampleDataTests(unittest.TestCase):
    def test_sample_data_matches_readme(self):
        accounts = cart.load_lines(os.path.join(DATA, "order_lines.csv"))
        inv = cart.load_inventory(os.path.join(DATA, "inventory.csv"))
        rows = cart.run(accounts, inv, AS_OF)
        self.assertEqual([r["account"] for r in rows],
                         ["Harbor Light Co-op", "North Fork Provisions", "Cedar Street Shop"])
        self.assertEqual([r["cart_total"] for r in rows], [696.0, 232.0, 360.0])


if __name__ == "__main__":
    unittest.main()

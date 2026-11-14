"""Reorder Cart: build a suggested reorder for every account that's about to be due.

Reorder Radar tells you who's late. This tells you who's about to be due and
what to put in their cart, so you can reach out right before they reorder
instead of after.

For each account it:
  1. works out its usual gap between orders (the median, same as radar.py)
  2. keeps it only if its next order lands 3 days early to 2 days late
  3. skips it if it already has an open order
  4. builds a cart by product TYPE, not by strain/flavor/variety, because
     those rotate. If they always take 100 "1g Pre-Roll" and the one they
     had is gone, it fills the line with another 1g Pre-Roll you have.
  5. adds up to 2 things they've never bought, from categories they buy
  6. holds stock back as it goes, so two accounts aren't promised the same units

Nothing is sent anywhere. It writes a list for a person to look over.

Usage:
  python cart.py data/order_lines.csv data/inventory.csv --as-of 2026-11-16
  python cart.py data/order_lines.csv data/inventory.csv --out carts.csv
"""
import argparse
import csv
import statistics
import sys
from datetime import date

EARLY_DAYS = 3        # start suggesting this many days before the usual next order
LATE_DAYS = 2         # ...and keep suggesting this many days after
MIN_ORDERS = 3        # need this many order days before we trust the pattern
OPEN_STATUSES = {"open", "approved", "in transit"}
TRY_NEW = 2           # products they've never bought, per cart


def product_type(product):
    """'Pine Haze - 1g Pre-Roll' -> '1g pre-roll'. No ' - ' means the name is the type."""
    parts = product.split(" - ", 1)
    return (parts[1] if len(parts) == 2 else parts[0]).strip().lower()


def load_lines(path):
    """Order lines -> {account: [orders]}, each order = {date, status, lines:[{product, qty, price, category}]}."""
    accounts = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        need = {"order_id", "order_date", "account", "status", "product", "category", "quantity", "unit_price"}
        missing = need - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"order lines CSV is missing column(s): {', '.join(sorted(missing))}")
        orders = {}
        for row in reader:
            oid = row["order_id"].strip()
            o = orders.setdefault(oid, {
                "account": row["account"].strip(),
                "date": date.fromisoformat(row["order_date"].strip()),
                "status": row["status"].strip().lower(),
                "lines": [],
            })
            o["lines"].append({
                "product": row["product"].strip(),
                "category": row["category"].strip(),
                "qty": float(row["quantity"]),
                "price": float(str(row["unit_price"]).replace("$", "").replace(",", "")),
            })
    for o in orders.values():
        accounts.setdefault(o["account"], []).append(o)
    return accounts


def load_inventory(path):
    """Inventory -> {product: {qty, price, category}}. Price is the current list price."""
    inv = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qty = float(row["available"] or 0)
            if qty <= 0:
                continue
            inv[row["product"].strip()] = {
                "qty": qty,
                "price": float(str(row["list_price"]).replace("$", "").replace(",", "") or 0),
                "category": row["category"].strip(),
            }
    return inv


def build_cart(orders, inv, as_of):
    """One account's suggested cart, or None if it isn't due in the window. Changes inv (holds stock)."""
    if any(o["status"] in OPEN_STATUSES for o in orders):
        return None
    done = [o for o in orders if o["status"] not in OPEN_STATUSES]
    days = sorted({o["date"] for o in done})
    if len(days) < MIN_ORDERS:
        return None
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    usual_gap = round(statistics.median(gaps))
    last = days[-1]
    days_from_due = (as_of - last).days - usual_gap  # + means late
    if days_from_due < -EARLY_DAYS or days_from_due > LATE_DAYS:
        return None

    by_day = {}
    for o in done:
        by_day[o["date"]] = by_day.get(o["date"], 0) + sum(l["qty"] * l["price"] for l in o["lines"])
    avg_order = sum(by_day.values()) / len(by_day)

    # What they usually take, by product type, over their last 3 order days
    last3 = set(days[-3:])
    types = {}
    for o in done:
        if o["date"] not in last3:
            continue
        for l in o["lines"]:
            t = types.setdefault(product_type(l["product"]), {"per_day": {}, "had": set()})
            t["per_day"][o["date"]] = t["per_day"].get(o["date"], 0) + l["qty"]
            t["had"].add(l["product"])
    usual = {k: v for k, v in types.items() if len(v["per_day"]) >= 2} or {
        k: v for k, v in types.items() if last in v["per_day"]}

    ever = {l["product"] for o in orders for l in o["lines"]}
    cart, flags, used = [], [], set()
    for ptype, t in sorted(usual.items()):
        want = round(statistics.median(t["per_day"].values()))
        options = sorted(
            (p for p, it in inv.items() if product_type(p) == ptype and it["qty"] > 0 and p not in used),
            key=lambda p: (p not in ever, -inv[p]["qty"]),  # things they've had first, then most stock
        )[:2]
        if not options:
            flags.append(f"Nothing in stock for {ptype}")
            continue
        left = want
        for i, p in enumerate(options):
            ask = left if i == len(options) - 1 else -(-want // len(options))
            qty = int(min(ask, inv[p]["qty"]))
            if qty <= 0:
                continue
            inv[p]["qty"] -= qty  # hold it so the next account can't be promised it too
            used.add(p)
            left -= qty
            cart.append({"product": p, "qty": qty, "price": inv[p]["price"],
                         "note": "" if p in t["had"] else "different variety, same type"})
        if left > 0:
            flags.append(f"Short {int(left)} of {ptype}")

    cats = {l["category"] for o in orders for l in o["lines"]}
    try_new = [p for p in sorted(inv, key=lambda p: -inv[p]["qty"])
               if p not in ever and p not in used and inv[p]["qty"] > 0 and inv[p]["category"] in cats][:TRY_NEW]

    total = sum(c["qty"] * c["price"] for c in cart)
    if cart and total < avg_order * 0.5:
        flags.append("Cart is under half their average")
    if cart and total > avg_order * 1.5:
        flags.append("Cart is 50%+ over their average")
    if any(c["price"] == 0 for c in cart):
        flags.append("Some lines have no list price, set one before sending")

    return {"usual_gap": usual_gap, "last_order": last.isoformat(), "days_from_due": days_from_due,
            "avg_order": round(avg_order, 2), "cart": cart, "cart_total": round(total, 2),
            "try_new": try_new, "flags": flags}


def run(accounts, inv, as_of):
    """Biggest accounts first, so they get first claim on limited stock."""
    def spend(orders):
        return sum(l["qty"] * l["price"] for o in orders for l in o["lines"])
    out = []
    for account in sorted(accounts, key=lambda a: -spend(accounts[a])):
        r = build_cart(accounts[account], inv, as_of)
        if r:
            r["account"] = account
            out.append(r)
    return out


def print_carts(rows, as_of):
    print(f"Reorder Cart, as of {as_of.isoformat()}: {len(rows)} account(s) due\n")
    for r in rows:
        when = f"{r['days_from_due']} day{'s' if r['days_from_due'] > 1 else ''} late" if r["days_from_due"] > 0 else (
            "due today" if r["days_from_due"] == 0 else f"due in {-r['days_from_due']} day{'s' if r['days_from_due'] < -1 else ''}")
        print(f"{r['account']}: {when}, orders every {r['usual_gap']} days, avg ${r['avg_order']:,.0f}")
        for c in r["cart"]:
            note = f"  ({c['note']})" if c["note"] else ""
            print(f"   {c['qty']:>4} x {c['product']} @ ${c['price']:.2f}{note}")
        print(f"   Cart total: ${r['cart_total']:,.2f}")
        if r["try_new"]:
            print(f"   Never tried: {', '.join(r['try_new'])}")
        for flag in r["flags"]:
            print(f"   ! {flag}")
        print()


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["account", "days_from_due", "usual_gap", "avg_order", "product", "qty", "price", "note", "flags"])
        for r in rows:
            for c in r["cart"] or [{"product": "", "qty": "", "price": "", "note": ""}]:
                w.writerow([r["account"], r["days_from_due"], r["usual_gap"], r["avg_order"],
                            c["product"], c["qty"], c["price"], c["note"], "; ".join(r["flags"])])


def main(argv=None):
    p = argparse.ArgumentParser(description="Build suggested reorder carts for accounts that are about to be due.")
    p.add_argument("order_lines_csv")
    p.add_argument("inventory_csv")
    p.add_argument("--as-of", help="Day to measure from, YYYY-MM-DD (default: today)")
    p.add_argument("--out", help="Also save the carts to this CSV file")
    args = p.parse_args(argv)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    try:
        accounts = load_lines(args.order_lines_csv)
        inv = load_inventory(args.inventory_csv)
    except (OSError, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    rows = run(accounts, inv, as_of)
    print_carts(rows, as_of)
    if args.out:
        write_csv(rows, args.out)
        print(f"Saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

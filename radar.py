"""Reorder Radar: find wholesale accounts that are late on their next order.

Reads a CSV of past orders (order_date, account, order_total) and gives each
account a status based on how often it usually orders:

  Overdue   more than 7 days past its usual gap between orders
  Due now   at or up to 7 days past its usual gap
  Lapsed    no order in 120+ days, or 3x its usual gap, whichever is longer
  New       only one order so far, so there is no pattern yet
  On track  not due yet

Usage:
  python radar.py data/orders.csv
  python radar.py data/orders.csv --as-of 2026-11-02 --out radar.csv
"""
import argparse
import csv
import statistics
import sys
from datetime import date

GRACE_DAYS = 7         # days past the usual gap before an account counts as overdue
LAPSED_MIN_DAYS = 120  # an account is lapsed after this many days, at minimum
LAPSED_MULTIPLE = 3    # ...or after this many usual gaps, whichever is longer

STATUS_ORDER = ["Overdue", "Due now", "Lapsed", "New", "On track"]


def load_orders(path):
    """Return {account: [order dates]} and {account: [order totals]} from the CSV."""
    dates, totals = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = {"order_date", "account", "order_total"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing column(s): {', '.join(sorted(missing))}")
        for line_no, row in enumerate(reader, start=2):
            account = (row["account"] or "").strip()
            if not account:
                continue
            try:
                d = date.fromisoformat(row["order_date"].strip())
            except ValueError:
                raise ValueError(f"Line {line_no}: bad date {row['order_date']!r}, use YYYY-MM-DD")
            try:
                total = float(str(row["order_total"]).replace("$", "").replace(",", ""))
            except ValueError:
                raise ValueError(f"Line {line_no}: bad order_total {row['order_total']!r}")
            dates.setdefault(account, []).append(d)
            totals.setdefault(account, []).append(total)
    return dates, totals


def score_account(order_dates, order_totals, as_of):
    """Work out one account's ordering pattern and status as of a given day."""
    days = sorted(set(order_dates))  # two orders on the same day count as one
    last = days[-1]
    days_since = (as_of - last).days
    avg_order = round(sum(order_totals) / len(order_totals), 2)
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    usual_gap = round(statistics.median(gaps)) if gaps else None

    if usual_gap is None:
        status = "Lapsed" if days_since >= LAPSED_MIN_DAYS else "New"
        days_late = None
    else:
        days_late = days_since - usual_gap
        if days_since >= max(LAPSED_MIN_DAYS, LAPSED_MULTIPLE * usual_gap):
            status = "Lapsed"
        elif days_late > GRACE_DAYS:
            status = "Overdue"
        elif days_late >= 0:
            status = "Due now"
        else:
            status = "On track"

    return {
        "status": status,
        "last_order": last.isoformat(),
        "days_since": days_since,
        "usual_gap": usual_gap,
        "days_late": days_late,
        "orders": len(days),
        "avg_order": avg_order,
    }


def run_radar(dates, totals, as_of):
    """Score every account and sort them so the ones to call first come first."""
    rows = []
    for account in dates:
        r = score_account(dates[account], totals[account], as_of)
        r["account"] = account
        rows.append(r)
    rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), -(r["days_late"] or 0), -r["avg_order"]))
    return rows


def print_table(rows, as_of):
    print(f"Reorder Radar, as of {as_of.isoformat()}\n")
    header = f"{'Status':<9} {'Account':<24} {'Last order':<11} {'Days since':>10} {'Usual gap':>9} {'Days late':>9} {'Avg order':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        gap = "-" if r["usual_gap"] is None else r["usual_gap"]
        late = "-" if r["days_late"] is None else r["days_late"]
        print(f"{r['status']:<9} {r['account'][:24]:<24} {r['last_order']:<11} {r['days_since']:>10} {gap:>9} {late:>9} {'$' + format(r['avg_order'], ',.0f'):>10}")


def write_csv(rows, path):
    cols = ["status", "account", "last_order", "days_since", "usual_gap", "days_late", "orders", "avg_order"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})


def main(argv=None):
    p = argparse.ArgumentParser(description="Find wholesale accounts that are late on their next order.")
    p.add_argument("orders_csv", help="CSV with columns order_date, account, order_total")
    p.add_argument("--as-of", help="Day to measure from, YYYY-MM-DD (default: today)")
    p.add_argument("--out", help="Also save the results to this CSV file")
    args = p.parse_args(argv)

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    try:
        dates, totals = load_orders(args.orders_csv)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not dates:
        print("No orders found in that file.", file=sys.stderr)
        return 1
    rows = run_radar(dates, totals, as_of)
    print_table(rows, as_of)
    if args.out:
        write_csv(rows, args.out)
        print(f"\nSaved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

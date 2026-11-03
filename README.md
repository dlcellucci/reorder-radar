# Reorder Radar

Find the wholesale accounts that have gone quiet before you lose the shelf.

## Why I built this

I run sales for a craft cannabis farm in Maine. I'm on my phone all day between meetings, ops and calls, and I kept losing track of who I should actually be calling. Notes on paper, numbers in five spreadsheets, and half the day gone just figuring out the day.

When a store goes quiet, it's usually because another brand took some or all of my shelf space. A few weeks past their normal reorder turns into a few months, and then I'm back to dropping samples and pulling a discount just to get back in. Catching it early is the difference between a quick reorder and starting the relationship over.

Reorder Radar looks at your past orders, learns how often each account usually buys, and tells you who's late, ranked so the biggest accounts come first.

It's built for anyone running sales for a producer with a lot of accounts that reorder on a regular rhythm. Farms, food, makers, cannabis. Somewhere around $1–5M a year is the sweet spot, but the math doesn't care about size.

— Dan Cellucci

## What it tells you

Each account gets one status:

| Status | Meaning |
|---|---|
| **Overdue** | More than 7 days past its usual time between orders |
| **Due now** | At, or up to 7 days past, its usual time between orders |
| **Lapsed** | No order in 120+ days, or 3x its usual gap, whichever is longer |
| **New** | Only one order so far, so there's no pattern yet |
| **On track** | Not due yet |

The list is sorted Overdue, Due now, Lapsed, New, On track. Inside each group, the biggest accounts (by average order) come first.

"Usual gap" is the middle gap between an account's orders (the median), so one weird holiday gap doesn't throw it off. Two orders on the same day count as one.

## Run it

You need Python 3.9 or newer. Nothing else to install.

```bash
git clone https://github.com/dlcellucci/reorder-radar.git
cd reorder-radar
python radar.py data/orders.csv --as-of 2026-11-02
```

Leave off `--as-of` to measure from today. Add `--out radar.csv` to save the results as a spreadsheet.

Example output with the sample data:

```
Status    Account                  Last order  Days since Usual gap Days late  Avg order
----------------------------------------------------------------------------------------
Overdue   Harbor Light Co-op       2026-10-03          30        19        11     $2,525
Overdue   Old Mill Mercantile      2026-09-03          60        34        26     $1,437
Overdue   Riverbend Supply         2026-10-07          26        14        12       $701
Due now   North Fork Provisions    2026-09-30          33        27         6     $1,765
Lapsed    Blue Ridge Grocers       2026-06-15         140        30       110       $877
New       Summit Farm Stand        2026-10-21          12         -         -       $520
On track  Cedar Street Shop        2026-10-13          20        46       -26     $3,049
On track  Pine Hollow Market       2026-10-23          10        15        -5     $1,069
```

## Use your own orders

Export your orders to a CSV with these three columns (one row per order):

```
order_date,account,order_total
2026-10-03,Harbor Light Co-op,2556.75
```

- `order_date` must be `YYYY-MM-DD`
- `order_total` can include `$` and commas
- Take closed accounts out first, or they'll show up as Lapsed forever

Your order data stays on your computer. Nothing is sent anywhere.

## Where it can be wrong

- Accounts that order on a wild schedule (10 days, then 90) get a usual gap that doesn't mean much.
- It only knows what's in the CSV. It doesn't know a store closed, changed buyers, or told you they're overstocked.
- It's a call list, not a crystal ball. Use it to decide who to call first, then talk to them.

## Check it works

```bash
python -m unittest discover tests
```

The tests check every rule edge (exactly 7 days late is Due now, 8 is Overdue) and that the sample data comes out exactly as shown above. If you change a rule, a test should fail. That's on purpose.

## Sample data

`data/orders.csv` is 48 made-up orders from 8 made-up stores. No real customers.

## License

MIT. Use it, change it, sell with it.

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

The radar tests check every rule edge (exactly 7 days late is Due now, 8 is Overdue) and that the sample data comes out exactly as shown above. If you change a rule, a test should fail. That's on purpose. The cart tests check the due window (3 early is in, 4 is out), that it never promises more than you have, that stock is held between accounts, and that the sample data comes out exactly as shown below.

## Reorder Cart: who's about to be due, and what to send them

The radar tells you who's already late. `cart.py` gets you there first. Every account whose next order lands **3 days early to 2 days late** on its own rhythm gets a suggested cart built from what you actually have in stock.

```bash
python cart.py data/order_lines.csv data/inventory.csv --as-of 2026-11-16
```

```
Harbor Light Co-op: due today, orders every 14 days, avg $704
     24 x Colombia Huila - 12oz Bag @ $9.50
     24 x Ethiopia Guji - 12oz Bag @ $9.50
      2 x Ethiopia Guji - 5lb Bag @ $62.00
      2 x Guatemala Antigua - 5lb Bag @ $58.00  (different variety, same type)
   Cart total: $696.00
   Never tried: Kenya AA - 12oz Bag, Decaf Swiss Water - 12oz Bag

North Fork Provisions: 2 days late, orders every 30 days, avg $580
      4 x Guatemala Antigua - 5lb Bag @ $58.00
   Cart total: $232.00
   Never tried: Cold Brew Pack - 2lb Bag
   ! Short 6 of 5lb bag
   ! Cart is under half their average
```

How it builds the cart:

- **By product type, not variety.** Varieties rotate. If an account always takes 48 "12oz Bag" and their usual one is gone, it fills the line with another 12oz Bag you have, and marks it so you can check.
- **Their usual amount.** The middle (median) quantity of each type over their last 3 orders.
- **One or two things they've never bought**, from categories they already buy.
- **It holds stock as it goes.** Bigger accounts get first claim, so two accounts are never promised the same units. North Fork comes up short above because Harbor Light already claimed the 5lb bags.
- **It skips** accounts with an open order and accounts with fewer than 3 orders.

The `!` lines are the point. A cart under half their usual order, a line with no price, or a type you're out of is a cart a person needs to look at before it goes anywhere.

The real problem it found for me: my biggest accounts' carts came up way short. The bottleneck wasn't getting the next order, it was having product made and out the door in time.

Your order lines CSV needs `order_id, order_date, account, status, product, category, quantity, unit_price`. Inventory needs `product, category, available, list_price`. Products are named `Variety - Type` (like `Kenya AA - 12oz Bag`); the part after ` - ` is the type.

### Where the cart can be wrong

- It trusts your list prices. A $0 list price gets flagged, but a stale one doesn't.
- "Same type, different variety" is a guess. Some buyers only want one specific variety.
- It doesn't know a buyer is overstocked, closed, or just switched brands.
- It suggests. It never sends. A person approves every cart.

## Failure alarm

`alarm/` has a two-box n8n workflow that Slack-messages you the moment any automation fails. See [alarm/README.md](alarm/README.md).

## Sample data

`data/orders.csv` is 48 made-up orders from 8 made-up stores. `data/order_lines.csv` and `data/inventory.csv` are a made-up coffee roaster's order lines and stock. No real customers.

## License

MIT. Use it, change it, sell with it.

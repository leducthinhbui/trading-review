"""What did each stock do in the 3 months after every sale (and every buy)?

    python after_trade.py trades_raw.txt prices out_dir

Writes sells.csv, buys.csv, summary.json and holdings.csv into out_dir.
Prices are daily closes from Yahoo Finance. The trade price is the cash amount
plus the A$/US$3 brokerage fee, divided by shares.
"""
import csv
import datetime as dt
import json
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict, deque

TRADES, PRICES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FEE = 3.0
YAHOO = {"BRK.B": "BRK-B", "PLS": "PLS.AX", "XRO": "XRO.AX", "MQG": "MQG.AX"}
NAMES = {
    "NVDA": "NVIDIA", "SNDK": "Sandisk", "AXP": "American Express", "CVS": "CVS Health", "CRDO": "Credo Technology",
    "META": "Meta Platforms", "MSTR": "MicroStrategy", "BRK.B": "Berkshire Hathaway", "TSM": "TSMC", "GLD": "SPDR Gold ETF",
    "VST": "Vistra", "AVGO": "Broadcom", "DVN": "Devon Energy", "MU": "Micron", "GOOGL": "Alphabet", "XOM": "Exxon Mobil",
    "JPM": "JPMorgan Chase", "MSFT": "Microsoft", "AAPL": "Apple", "JEPQ": "JPMorgan Nasdaq Income ETF", "AMD": "AMD",
    "PLTR": "Palantir", "GS": "Goldman Sachs", "MFG": "Mizuho Financial", "INTC": "Intel", "PLS": "Pilbara Minerals",
    "XRO": "Xero", "MQG": "Macquarie Group",
}
THEMES = {
    "AI chips and hardware": {"NVDA", "SNDK", "CRDO", "TSM", "AVGO", "MU", "AMD", "INTC"},
    "Big tech": {"META", "GOOGL", "MSFT", "AAPL", "PLTR"},
    "Financials": {"AXP", "BRK.B", "JPM", "GS", "MFG", "MQG", "XRO"},
    "Energy and power": {"XOM", "DVN", "VST"},
    "Gold and bitcoin": {"GLD", "MSTR"},
    "Healthcare": {"CVS"},
    "Lithium": {"PLS"},
    "Income ETF": {"JEPQ"},
}
theme_of = {code: t for t, codes in THEMES.items() for code in codes}


def load_prices(ticker):
    rows = list(csv.DictReader(open(f"{PRICES}/{ticker.replace('^', '')}.csv")))
    return [dt.date.fromisoformat(r["date"]) for r in rows], [float(r["close"]) for r in rows]


prices = {}


def series(code, market):
    key = YAHOO.get(code, code)
    if key not in prices:
        prices[key] = load_prices(key)
    return prices[key]


bench = {"US": load_prices("SPY"), "ASX": load_prices("AXJO")}


def close_on_or_after(dates, closes, day):
    i = bisect_left(dates, day)
    return (dates[i], closes[i]) if i < len(dates) else (None, None)


def close_on_or_before(dates, closes, day):
    i = bisect_right(dates, day) - 1
    return (dates[i], closes[i]) if i >= 0 else (None, None)


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.date(y, m, day)


def window(code, market, day, base_price):
    """Price change 1 and 3 months after `day`, the best and worst point in between, and the market's move."""
    dates, closes = series(code, market)
    last = dates[-1]
    end = add_months(day, 3)
    complete = end <= last
    end_used = end if complete else last
    d1, p1 = close_on_or_before(dates, closes, min(add_months(day, 1), last))
    d3, p3 = close_on_or_before(dates, closes, end_used)
    i0, i1 = bisect_right(dates, day), bisect_right(dates, end_used)
    seg = closes[i0:i1] or [p3]
    bd, bc = bench[market]
    _, b0 = close_on_or_before(bd, bc, day)
    _, b3 = close_on_or_before(bd, bc, end_used)
    return {
        "chg_1m": (p1 / base_price - 1) * 100 if day < last else None,
        "chg_3m": (p3 / base_price - 1) * 100,
        "max_3m": (max(seg) / base_price - 1) * 100,
        "min_3m": (min(seg) / base_price - 1) * 100,
        "market_3m": (b3 / b0 - 1) * 100,
        "price_3m": p3,
        "window_end": d3.isoformat(),
        "complete": complete,
        "days": (end_used - day).days,
    }


trades = {"US": [], "ASX": []}
market = None
for line in open(TRADES):
    line = line.strip()
    if line.startswith("WALL ST"):
        market = "US"; continue
    if line.startswith("ASX"):
        market = "ASX"; continue
    d, code, side, qty, amt = line.split("|")
    qty, amt = float(qty), float(amt)
    price = (amt + FEE) / qty if side == "Sell" else (-amt - FEE) / qty
    trades[market].append({"date": dt.datetime.strptime(d, "%d %b %Y").date(), "code": code, "side": side,
                           "qty": qty, "amount": amt, "price": price, "market": market})

sells, buys = [], []
for mkt, rows in trades.items():
    rows.sort(key=lambda r: (r["date"], r["side"] == "Sell"))
    lots = defaultdict(deque)
    for r in rows:
        if r["side"] == "Buy":
            lots[r["code"]].append([r["qty"], -r["amount"] / r["qty"], r["date"]])
            w = window(r["code"], mkt, r["date"], r["price"])
            buys.append({**r, **w})
            continue
        left, cost, first = r["qty"], 0.0, None
        while left > 1e-9:
            lot = lots[r["code"]][0]
            take = min(left, lot[0]); cost += take * lot[1]; first = first or lot[2]
            lot[0] -= take; left -= take
            if lot[0] <= 1e-9:
                lots[r["code"]].popleft()
        w = window(r["code"], mkt, r["date"], r["price"])
        profit = r["amount"] - cost
        # Positive "missed" means the stock kept rising after the sale; negative means a fall was avoided.
        missed = r["qty"] * (w["price_3m"] - r["price"])
        if w["chg_3m"] <= -5:
            verdict = "Good sell"
        elif w["chg_3m"] >= 5:
            verdict = "Sold early"
        else:
            verdict = "About even"
        sells.append({**r, **w, "profit": profit, "profit_pct": profit / cost * 100, "held_days": (r["date"] - first).days,
                      "missed": missed, "verdict": verdict})
    held = {c: q for c, q in lots.items() if sum(l[0] for l in q) > 1e-9}
    if mkt == "US":
        holdings = []
        for code, q in held.items():
            dates, closes = series(code, mkt)
            shares = sum(l[0] for l in q); cost = sum(l[0] * l[1] for l in q)
            holdings.append({"code": code, "name": NAMES[code], "shares": shares, "avg_cost": cost / shares,
                             "last_close": closes[-1], "last_date": dates[-1].isoformat(),
                             "return_pct": (closes[-1] * shares / cost - 1) * 100, "theme": theme_of[code]})

fmt = lambda v, n=2: None if v is None else round(v, n)
with open(f"{OUT}/sells.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "date", "market", "code", "name", "theme", "shares", "sell_price", "profit", "profit_pct", "held_days",
                "chg_1m_pct", "chg_3m_pct", "max_3m_pct", "min_3m_pct", "market_3m_pct", "price_3m", "window_end",
                "window_complete", "missed_or_avoided", "verdict"])
    for i, s in enumerate(sorted(sells, key=lambda s: s["date"]), 1):
        w.writerow([f"S{i:02d}", s["date"].isoformat(), s["market"], s["code"], NAMES[s["code"]], theme_of[s["code"]],
                    s["qty"], fmt(s["price"]), fmt(s["profit"]), fmt(s["profit_pct"], 1), s["held_days"], fmt(s["chg_1m"], 1),
                    fmt(s["chg_3m"], 1), fmt(s["max_3m"], 1), fmt(s["min_3m"], 1), fmt(s["market_3m"], 1), fmt(s["price_3m"]),
                    s["window_end"], "yes" if s["complete"] else "no", fmt(s["missed"]), s["verdict"]])
with open(f"{OUT}/buys.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "market", "code", "name", "shares", "buy_price", "chg_3m_pct", "market_3m_pct", "window_complete"])
    for b in sorted(buys, key=lambda b: b["date"]):
        w.writerow([b["date"].isoformat(), b["market"], b["code"], NAMES[b["code"]], b["qty"], fmt(b["price"]),
                    fmt(b["chg_3m"], 1), fmt(b["market_3m"], 1), "yes" if b["complete"] else "no"])
with open(f"{OUT}/holdings.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["code", "name", "theme", "shares", "avg_cost", "last_close", "last_date", "return_pct"])
    for h in holdings:
        w.writerow([h["code"], h["name"], h["theme"], h["shares"], fmt(h["avg_cost"]), fmt(h["last_close"]), h["last_date"],
                    fmt(h["return_pct"], 1)])

us = [s for s in sells if s["market"] == "US"]
complete = [s for s in sells if s["complete"]]
summary = {
    "sells": len(sells), "sells_us": len(us), "sells_complete": len(complete),
    "profitable_sells_us": sum(1 for s in us if s["profit"] > 0),
    "realised_us": sum(s["profit"] for s in us), "realised_asx": sum(s["profit"] for s in sells if s["market"] == "ASX"),
    "good_sells": sum(1 for s in complete if s["verdict"] == "Good sell"),
    "sold_early": sum(1 for s in complete if s["verdict"] == "Sold early"),
    "about_even": sum(1 for s in complete if s["verdict"] == "About even"),
    "avg_3m_after_sell": sum(s["chg_3m"] for s in complete) / len(complete),
    "avg_market_3m": sum(s["market_3m"] for s in complete) / len(complete),
    "missed_us": sum(s["missed"] for s in us if s["complete"]),
    "first_trade": min(t["date"] for r in trades.values() for t in r).isoformat(),
    "trades": sum(len(r) for r in trades.values()),
    "stocks": len({t["code"] for r in trades.values() for t in r}),
}
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))


# Did buying after a drop work? A "dip buy" is a buy where the stock had fallen 5% or more
# from its highest close in the 20 trading days before the buy.
dip_rows = []
for b in buys:
    dates, closes = series(b["code"], b["market"])
    i = bisect_left(dates, b["date"])
    prior = closes[max(0, i - 20):i]
    drop = (b["price"] / max(prior) - 1) * 100 if prior else 0
    dip_rows.append({**b, "drop_before": drop, "dip": drop <= -5})
with open(f"{OUT}/buys.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "market", "code", "name", "shares", "buy_price", "drop_before_pct", "dip_buy", "chg_3m_pct",
                "market_3m_pct", "window_complete"])
    for b in sorted(dip_rows, key=lambda b: b["date"]):
        w.writerow([b["date"].isoformat(), b["market"], b["code"], NAMES[b["code"]], b["qty"], fmt(b["price"]),
                    fmt(b["drop_before"], 1), "yes" if b["dip"] else "no", fmt(b["chg_3m"], 1), fmt(b["market_3m"], 1),
                    "yes" if b["complete"] else "no"])
done = [b for b in dip_rows if b["complete"]]
avg = lambda xs: sum(xs) / len(xs) if xs else None
summary.update({
    "buys_complete": len(done),
    "dip_buys": sum(1 for b in done if b["dip"]),
    "dip_buy_avg_3m": avg([b["chg_3m"] for b in done if b["dip"]]),
    "other_buy_avg_3m": avg([b["chg_3m"] for b in done if not b["dip"]]),
    "dip_buy_win_rate": avg([100.0 if b["chg_3m"] > 0 else 0.0 for b in done if b["dip"]]),
    "other_buy_win_rate": avg([100.0 if b["chg_3m"] > 0 else 0.0 for b in done if not b["dip"]]),
    "buy_market_avg_3m": avg([b["market_3m"] for b in done]),
})
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in summary.items() if k.startswith(("buy", "dip", "other"))})

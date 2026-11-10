"""FIFO realised profit per stock from trades_raw.txt (amounts are cash after fees)."""
import sys, datetime
from collections import defaultdict, deque
path = sys.argv[1]
market = None; trades = {"WALL ST (USD)": [], "ASX (AUD)": []}
for line in open(path):
    line = line.strip()
    if line in trades: market = line; continue
    d, code, side, qty, amt = line.split("|")
    trades[market].append((datetime.datetime.strptime(d, "%d %b %Y"), code, side, float(qty), float(amt)))
for m, rows in trades.items():
    rows.sort(key=lambda r: (r[0], r[2] == "Sell"))   # buys before sells on the same day
    lots = defaultdict(deque); realised = defaultdict(float); closed = []
    for dt, code, side, qty, amt in rows:
        if side == "Buy":
            lots[code].append([qty, -amt / qty, dt])
        else:
            proceeds_per = amt / qty; left = qty; cost = 0; first = None
            while left > 1e-9:
                lot = lots[code][0]; take = min(left, lot[0]); cost += take * lot[1]; first = first or lot[2]
                lot[0] -= take; left -= take
                if lot[0] <= 1e-9: lots[code].popleft()
            pnl = amt - cost; realised[code] += pnl
            closed.append((code, dt, pnl, pnl / cost * 100, (dt - first).days))
    total = sum(realised.values())
    wins = [c for c in closed if c[2] > 0]
    print(f"\n== {m}: {len(rows)} trades, {len(closed)} sells, realised profit {total:,.2f}")
    print(f"   winning sells {len(wins)}/{len(closed)} ({len(wins)/len(closed)*100:.0f}%), median hold {sorted(c[4] for c in closed)[len(closed)//2]} days")
    for code, v in sorted(realised.items(), key=lambda kv: -kv[1]):
        print(f"   {code:6} {v:10,.2f}")
    open_lots = {c: (sum(l[0] for l in q), sum(l[0]*l[1] for l in q)) for c, q in lots.items() if sum(l[0] for l in q) > 1e-9}
    print("   still held (shares, cost):", {c: (round(s, 2), round(cst, 2)) for c, (s, cst) in open_lots.items()})

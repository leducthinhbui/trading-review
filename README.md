# Trading Review: Did I Sell at the Right Time?

A review of my own share trades on Stake since March 2025: 97 trades across 27 US and ASX stocks and ETFs. For every sale I measured what the stock did over the next three months and compared it with the market. For every buy I checked whether buying after a price drop paid off.

**Live dashboard:** https://leducthinhbui.github.io/trading-review/

## Findings

- **Track record:** 22% all-time return (as shown in the Stake app). 30 of 42 US sales (71%) closed at a profit, for US$4,455 of realised profit after brokerage.
- **Timing of sales:** of the 27 sales with a full three months of data, 4 were good sells (the stock fell 5% or more afterwards), 14 were sold early (it rose 5% or more) and 9 were about even. On average a stock I sold rose 15.5% over the next three months, against 4.2% for the market.
- **Recent exits were well timed:** I sold Sandisk, Micron, Broadcom, Credo, MicroStrategy and gold in August and September 2026, before the October sell-off in AI and chip stocks. Sandisk is 47% below my sale price so far.
- **Earlier, I sold winners too soon:** AMD rose 132% in the three months after I sold, NVIDIA (May 2025) 51%, and Microsoft 32% after I sold it at a loss near its yearly low.
- **Buying after a drop beat the market but not my other buys:** dip buys gained 10.6% on average over three months (up 80% of the time), my other buys 16.5%, and the market 5.2%.
- **Current holdings:** NVIDIA and Sandisk for AI computing and storage demand, bought more after price drops, with CVS Health as a defensive, dividend-paying balance.

## Files

| Path | What it holds |
|---|---|
| `index.html` | The dashboard (static page, charts drawn with d3) |
| `data/trades.csv` | Every trade since March 2025: date, market, stock, side, shares, cash amount after brokerage |
| `data/sells.csv` | Each sale with my profit, the stock's change over the next three months, the market's change and a verdict |
| `data/buys.csv` | Each buy, whether it was a dip buy, and the change over the next three months |
| `data/holdings.csv` | Current holdings with average cost and return |
| `data/news.csv` | News behind the biggest moves, with links |
| `data/summary.json` | Headline figures used on the dashboard |
| `scripts/after_trade.py` | Builds the CSVs from the trade list and daily prices |
| `scripts/analyse_trades.py` | First-in, first-out profit per stock |

## Method

- **Prices:** daily closes from Yahoo Finance. "Three months later" compares my sale price with the close three calendar months after the sale. The market is the S&P 500 (SPY) for US stocks and the ASX 200 for Australian stocks.
- **Profit:** first-in, first-out cost basis, including the A$/US$3 brokerage on every trade.
- **Verdicts:** good sell if the stock was 5% or more lower three months later, sold early if 5% or more higher, about even in between. Sales from the last three months show the change so far.
- **Dip buy:** a purchase made at least 5% below the stock's highest close of the previous 20 trading days.

## Run it

Daily prices are in `prices/` (Yahoo Finance closes, columns `date,close`). To rebuild the analysis:

```bash
python scripts/after_trade.py data/trades_raw.txt prices data
```

To view the dashboard locally, serve the folder (for example `python -m http.server`) and open http://localhost:8000.

This is a personal record of my own trades, published as a portfolio project. Nothing here is a recommendation to buy or sell.

"""Download daily prices, dividends and FX for the coverage universe.

    uv run --no-project --with yfinance python scripts/fetch_market_data.py

Writes data/raw/market/{prices,dividends,fx}.csv (gitignored: market data is not redistributed).
Prices are unadjusted for dividends but adjusted for splits/consolidations, so a holding's unit
count stays consistent across the whole history. Prices and dividends are in the security's own
currency; fx.csv holds USD→SGD for the USD-quoted names.
"""

import csv
from datetime import date
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw" / "market"
START = "2020-01-01"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "universe.csv", encoding="utf-8") as f:
        universe = list(csv.DictReader(f))

    n_px = n_div = 0
    with (
        open(OUT / "prices.csv", "w", newline="") as fp,
        open(OUT / "dividends.csv", "w", newline="") as fd,
    ):
        px, dv = csv.writer(fp), csv.writer(fd)
        px.writerow(["yahoo_ticker", "date", "close"])
        dv.writerow(["yahoo_ticker", "ex_date", "amount"])
        for row in universe:
            t = yf.Ticker(row["yahoo_ticker"])
            hist = t.history(start=START, auto_adjust=False, actions=True)
            for ts, r in hist.iterrows():
                px.writerow(
                    [row["yahoo_ticker"], ts.date().isoformat(), f"{r['Close']:.4f}"]
                )
                n_px += 1
                if r.get("Dividends", 0):
                    dv.writerow(
                        [
                            row["yahoo_ticker"],
                            ts.date().isoformat(),
                            f"{r['Dividends']:.6f}",
                        ]
                    )
                    n_div += 1
            print(f"  {row['yahoo_ticker']:<9} {len(hist):>5} days")

    fx = yf.Ticker("SGD=X").history(start=START, auto_adjust=False)  # SGD per 1 USD
    with open(OUT / "fx.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ccy", "date", "rate_to_sgd"])
        for ts, r in fx.iterrows():
            w.writerow(["USD", ts.date().isoformat(), f"{r['Close']:.6f}"])
    print(
        f"prices: {n_px:,} rows · dividends: {n_div} · fx: {len(fx)} days · as of {date.today()}"
    )


if __name__ == "__main__":
    main()

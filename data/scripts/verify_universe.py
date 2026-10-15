"""Verify the coverage universe against live market data.

    uv run --no-project --with yfinance --with requests python scripts/verify_universe.py universe.csv

For each row: does the Yahoo ticker resolve, does the name match, what currency, is there price
and dividend history, and does the IR page respond? Prints a report; edits nothing.
"""

import csv
import sys

import requests
import yfinance as yf

# Several IR sites reject non-browser user agents (HTTP 403/405).
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/130 Safari/537.36"
}


def check_ir(url: str) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=10, allow_redirects=True)
        return str(r.status_code)
    except requests.RequestException as e:
        return type(e).__name__


def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(
        f"{'code':<5} {'yahoo name':<44} {'ccy':<4} {'last':>7} {'yrs px':>6} {'divs':>5} {'IR':>4}"
    )
    for row in rows:
        t = yf.Ticker(row["yahoo_ticker"])
        try:
            info = t.info
            hist = t.history(period="max", auto_adjust=False)
            divs = t.dividends
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"{row['sgx_code']:<5} ERROR {type(e).__name__}: {e}")
            continue
        if hist is None or len(hist) == 0:
            print(f"{row['sgx_code']:<5} NOT FOUND on Yahoo ({row['yahoo_ticker']})")
            continue
        divs = divs if divs is not None else []
        name = (info.get("longName") or info.get("shortName") or "?")[:44]
        years = (hist.index[-1] - hist.index[0]).days / 365 if len(hist) else 0
        last = hist["Close"].iloc[-1] if len(hist) else float("nan")
        print(
            f"{row['sgx_code']:<5} {name:<44} {info.get('currency', '?'):<4} {last:>7.3f} "
            f"{years:>6.1f} {len(divs):>5} {check_ir(row['ir_url']):>4}"
        )


if __name__ == "__main__":
    main(sys.argv[1])

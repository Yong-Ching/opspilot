"""Generate SYNTHETIC market-data fixtures for tests (no real market data is committed).

uv run python tests/fixtures/make_fixtures.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
UNIVERSE = [  # subset of data/universe.csv: SGD + USD REITs, a retired code, banks
    ("C38U", "CapitaLand Integrated Commercial Trust", "REIT", "Retail & Office", "SGD", 2.10),
    ("M44U", "Mapletree Logistics Trust", "REIT", "Logistics", "SGD", 1.20),
    ("AJBU", "Keppel DC REIT", "REIT", "Data Centre", "SGD", 2.00),
    ("DCRU", "Digital Core REIT", "REIT", "Data Centre", "USD", 0.55),
    ("9A4U", "ESR-REIT", "REIT", "Industrial", "SGD", 2.00),
    ("D05", "DBS Group Holdings", "Stock", "Banks", "SGD", 55.0),
    ("O39", "Oversea-Chinese Banking Corporation", "Stock", "Banks", "SGD", 17.0),
]


def main() -> None:
    rng = random.Random(7)
    days = [date(2025, 10, 1) + timedelta(days=i) for i in range(183)]
    days = [d for d in days if d.weekday() < 5]
    with open(HERE / "universe.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sgx_code", "yahoo_ticker", "name", "type", "sector", "currency", "sponsor",
                    "ir_url", "notes"])  # fmt: skip
        for code, name, typ, sector, ccy, _ in UNIVERSE:
            w.writerow([code, f"{code}.SI", name, typ, sector, ccy, "", "", "synthetic fixture"])
    with (
        open(HERE / "prices.csv", "w", newline="") as fp,
        open(HERE / "dividends.csv", "w", newline="") as fd,
    ):
        px, dv = csv.writer(fp), csv.writer(fd)
        px.writerow(["yahoo_ticker", "date", "close"])
        dv.writerow(["yahoo_ticker", "ex_date", "amount"])
        for code, _, typ, _, _, start in UNIVERSE:
            p = start
            for i, d in enumerate(days):
                p = max(0.05, p * (1 + rng.gauss(0.0002, 0.012)))
                px.writerow([f"{code}.SI", d.isoformat(), f"{p:.4f}"])
                if typ == "REIT" and i in (20, 85):  # two distributions in the window
                    dv.writerow([f"{code}.SI", d.isoformat(), f"{start * 0.015:.6f}"])
    with open(HERE / "fx.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ccy", "date", "rate_to_sgd"])
        for d in days:
            w.writerow(["USD", d.isoformat(), f"{1.30 + rng.uniform(-0.02, 0.02):.6f}"])


if __name__ == "__main__":
    main()

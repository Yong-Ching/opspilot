"""Synthetic Harbourfront Capital: staff, clients, funds, mandates and a trade history.

Everything here is fictional. Trades are simulated at REAL closing prices (loaded beforehand into
`prices`), so holdings, weights and P&L look like a real portfolio. Deterministic for a given seed.

Simplifications (documented on purpose):
- Dividend cash is booked on the ex-date (real funds receive it on the payment date).
- Fees are a flat 0.10% of notional (min S$25); no taxes, no slippage.
- Each security is its own "issuer" (sponsor groups are ignored for limits).
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import psycopg

USERS = [
    ("u_lim_jh", "Lim Jia Hui", "ANALYST", "RESEARCH"),
    ("u_raj_k", "Rajesh Kumar", "ANALYST", "RESEARCH"),
    ("u_nur_a", "Nurul Aisyah", "ANALYST", "RESEARCH"),
    ("u_tan_wl", "Tan Wei Ling", "PM", "PORTFOLIO"),
    ("u_ong_bk", "Ong Boon Keat", "PM", "PORTFOLIO"),
    ("u_chua_m", "Michelle Chua", "PM", "PORTFOLIO"),
    ("u_goh_sp", "Goh Siew Ping", "COMPLIANCE", "COMPLIANCE"),
    ("u_ng_d", "Daniel Ng", "RM", "WEALTH"),
    ("u_farah_i", "Farah Ismail", "RM", "WEALTH"),
]

REITS = ["C38U", "A17U", "M44U", "ME8U", "N2IU", "J69U", "BUOU", "K71U", "AJBU", "T82U",
         "C2PU", "HMN", "J85", "DCRU", "9A4U"]  # fmt: skip
BLUE_CHIPS = ["D05", "O39", "U11", "Z74", "BN4", "9CI", "C6L", "S63", "F34", "S68"]


@dataclass
class FundSpec:
    code: str
    name: str
    fund_type: str
    pm: str
    inception: date
    initial_sgd: int
    universe: list[str]
    rules: list[tuple[str, str | None, float | None, str]]  # (type, param, limit, description)
    client_index: int | None = None  # which generated client owns the mandate
    monthly_flows: bool = False
    cash_target_pct: float = 2.0


FUNDS = [
    FundSpec(
        "HCREIT",
        "HC Singapore REIT Income Fund",
        "UNIT_TRUST",
        "u_tan_wl",
        date(2021, 1, 4),
        80_000_000,
        REITS,
        [
            ("MAX_ISSUER_PCT", None, 15, "No single REIT above 15% of NAV"),
            ("MIN_REIT_PCT", None, 90, "At least 90% of NAV in REITs"),
            ("MAX_SECTOR_PCT", "Hospitality", 12, "Hospitality REITs at most 12% of NAV"),
            ("MIN_CASH_PCT", None, 1, "Keep at least 1% in cash"),
        ],
        monthly_flows=True,
    ),
    FundSpec(
        "HCDIV",
        "HC Singapore Dividend Fund",
        "UNIT_TRUST",
        "u_ong_bk",
        date(2021, 1, 4),
        120_000_000,
        BLUE_CHIPS + ["C38U", "A17U", "M44U", "J69U", "C2PU"],
        [
            ("MAX_ISSUER_PCT", None, 20, "No single issuer above 20% of NAV"),
            ("MAX_SECTOR_PCT", "Banks", 45, "Banks at most 45% of NAV"),
            ("EXCLUDE_SECURITY", "F34", None, "ESG exclusion: palm-oil deforestation policy"),
            ("MIN_CASH_PCT", None, 1, "Keep at least 1% in cash"),
        ],
        monthly_flows=True,
    ),
    FundSpec(
        "MND-001",
        "Segregated mandate (conservative income)",
        "MANDATE",
        "u_chua_m",
        date(2022, 3, 1),
        5_000_000,
        [
            "C38U",
            "A17U",
            "M44U",
            "J69U",
            "C2PU",
            "K71U",
            "T82U",
            "BUOU",
            "D05",
            "O39",
            "U11",
            "Z74",
        ],
        [
            ("MAX_ISSUER_PCT", None, 10, "No single issuer above 10% of NAV"),
            ("MAX_SECTOR_PCT", "Hospitality", 0, "Client excludes hospitality"),
            ("MIN_CASH_PCT", None, 3, "Keep at least 3% in cash"),
        ],
        client_index=2,
        cash_target_pct=4.0,
    ),
    FundSpec(
        "MND-002",
        "Segregated mandate (balanced dividend)",
        "MANDATE",
        "u_chua_m",
        date(2023, 7, 3),
        12_000_000,
        BLUE_CHIPS + ["C38U", "ME8U", "AJBU", "T82U"],
        [
            ("MAX_ISSUER_PCT", None, 12, "No single issuer above 12% of NAV"),
            (
                "EXCLUDE_SECURITY",
                "C6L",
                None,
                "Conflict: client is a senior employee of the issuer",
            ),
        ],
        client_index=5,
    ),
    FundSpec(
        "MND-003",
        "Segregated mandate (growth)",
        "MANDATE",
        "u_chua_m",
        date(2024, 2, 1),
        3_000_000,
        ["D05", "O39", "U11", "BN4", "9CI", "S63", "S68", "AJBU", "DCRU"],
        [("MAX_ISSUER_PCT", None, 25, "No single issuer above 25% of NAV")],
        client_index=11,
    ),
]

# ── synthetic clients ────────────────────────────────────────────────────────────────────────
SURNAMES = ["Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh", "Teo", "Ang",
            "Yeo", "Tay", "Ho", "Low", "Toh", "Sim", "Chong", "Chia"]  # fmt: skip
GIVEN = ["Wei Ming", "Hui Min", "Jun Jie", "Xin Yi", "Kok Leong", "Mei Ling", "Zhi Hao", "Li Ting",
         "Boon Hock", "Siew Lan", "Jia Wei", "Pei Shan"]  # fmt: skip
OTHER_NAMES = [
    "Muhammad Faizal bin Rahman", "Siti Nurhaliza binte Osman", "Ahmad Hafiz bin Ismail",
    "Nur Ain binte Yusof", "Mohamed Irfan bin Salleh", "Arun s/o Krishnan",
    "Priya d/o Subramaniam", "Ganesh s/o Rajan", "Kavitha d/o Muthu", "Daniel de Souza",
    "Rachel Pereira", "Vikram Menon",
]  # fmt: skip
TOWNS = [  # (street pattern, postal sector)
    ("Tampines St {n}", "52"), ("Ang Mo Kio Ave {n}", "56"), ("Bedok North St {n}", "46"),
    ("Jurong West St {n}", "64"), ("Punggol Field Walk", "82"), ("Toa Payoh Lor {n}", "31"),
    ("Clementi Ave {n}", "12"), ("Bishan St {n}", "57"), ("Sengkang East Way", "54"),
    ("Woodlands Dr {n}", "73"),
]  # fmt: skip

NRIC_WEIGHTS = [2, 7, 6, 5, 4, 3, 2]
NRIC_ST_LETTERS = "JZIHGFEDCBA"


def nric(prefix: str, digits: str) -> str:
    """NRIC with a valid checksum letter. Synthetic: any match to a real person is coincidental."""
    total = sum(int(d) * w for d, w in zip(digits, NRIC_WEIGHTS, strict=True))
    if prefix == "T":
        total += 4
    return f"{prefix}{digits}{NRIC_ST_LETTERS[total % 11]}"


def make_clients(rng: random.Random, n: int = 40) -> list[tuple[Any, ...]]:
    rms = ["u_ng_d", "u_farah_i"]
    rows: list[tuple[Any, ...]] = []
    for i in range(n):
        if rng.random() < 0.7:
            name = f"{rng.choice(SURNAMES)} {rng.choice(GIVEN)}"
        else:
            name = rng.choice(OTHER_NAMES)
        dob = date(1950, 1, 1) + timedelta(days=rng.randint(0, 365 * 50))
        ic = nric(
            "S" if dob.year < 2000 else "T", f"{dob.year % 100:02d}{rng.randint(0, 99999):05d}"
        )
        street, sector = rng.choice(TOWNS)
        address = (
            f"Blk {rng.randint(100, 899)} {street.format(n=rng.randint(1, 30))} "
            f"#{rng.randint(2, 25):02d}-{rng.randint(1, 499):03d} "
            f"Singapore {sector}{rng.randint(0, 9999):04d}"
        )
        handle = "".join(c for c in name.lower().split(" bin")[0].split(" s/o")[0] if c.isalpha())
        rows.append(
            (
                f"C{i + 1:05d}",
                name,
                ic,
                dob,
                f"{handle}{rng.randint(1, 99)}@example.com",
                f"+65 {rng.choice('89')}{rng.randint(0, 999):03d} {rng.randint(0, 9999):04d}",
                address,
                rng.choice(["CONSERVATIVE", "BALANCED", "BALANCED", "GROWTH"]),
                rms[i % 2],
                date(2020, 6, 1) + timedelta(days=rng.randint(0, 1500)),
            )
        )
    return rows


# ── trade simulation ─────────────────────────────────────────────────────────────────────────
CENT = Decimal("0.01")


def money(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Market:
    sec_by_code: dict[str, str]  # sgx_code -> security_id
    sector: dict[str, str]  # security_id -> sector
    currency: dict[str, str]
    board_lot: dict[str, int]
    px: dict[str, dict[date, float]]  # security_id -> date -> close (major units)
    divs: dict[date, list[tuple[str, float]]]  # ex_date -> [(security_id, amount)]
    fx: dict[date, float]  # USD -> SGD
    days: list[date]  # trading days (union of price dates)

    def fx_on(self, sid: str, d: date) -> float:
        if self.currency[sid] == "SGD":
            return 1.0
        for k in range(10):  # FX may be missing on SGX trading days
            v = self.fx.get(d - timedelta(days=k))
            if v:
                return v
        raise ValueError(f"no FX for {d}")


def load_market(conn: psycopg.Connection) -> Market:
    sec = conn.execute(
        "SELECT s.security_id, i.id_value, s.sector, s.currency, s.board_lot FROM securities s "
        "JOIN security_identifiers i ON i.security_id = s.security_id "
        "AND i.id_type = 'SGX' AND i.is_current"
    ).fetchall()
    px: dict[str, dict[date, float]] = {}
    for sid, d, minor in conn.execute("SELECT security_id, px_date, px_close_minor FROM prices"):
        px.setdefault(sid, {})[d] = minor / 100
    divs: dict[date, list[tuple[str, float]]] = {}
    for sid, d, amt in conn.execute("SELECT security_id, ex_date, amount FROM dividends"):
        divs.setdefault(d, []).append((sid, float(amt)))
    fx = {d: float(r) for d, r in conn.execute("SELECT fx_date, rate_to_sgd FROM fx_rates")}
    days = sorted({d for series in px.values() for d in series})
    return Market(
        sec_by_code={code: sid for sid, code, *_ in sec},
        sector={sid: s for sid, _, s, _, _ in sec},
        currency={sid: c for sid, _, _, c, _ in sec},
        board_lot={sid: b for sid, _, _, _, b in sec},
        px=px, divs=divs, fx=fx, days=days,
    )  # fmt: skip


@dataclass
class Book:
    cash: Decimal = Decimal(0)
    qty: dict[str, int] = field(default_factory=dict)


def _target_weights(
    rng: random.Random, sids: list[str], spec: FundSpec, mkt: Market
) -> dict[str, float]:
    """Random tilt around equal weight, respecting issuer and sector caps (with 1.5pp headroom).

    Water-filling: scale over-limit sectors down, clip issuers to the cap, hand the shortfall to
    names that still have room, repeat. Weight that cannot be placed stays in cash.
    """
    issuer_cap = next((r[2] for r in spec.rules if r[0] == "MAX_ISSUER_PCT"), None) or 100
    cap = (issuer_cap - 1.5) / 100
    sector_caps = {
        r[1]: max((r[2] or 0) - 1.5, 0) / 100 for r in spec.rules if r[0] == "MAX_SECTOR_PCT"
    }
    eligible = [s for s in sids if sector_caps.get(mkt.sector[s], 1.0) > 0]
    if not eligible:
        return {}
    invest = (100 - spec.cash_target_pct) / 100
    raw = {s: rng.uniform(0.6, 1.4) for s in eligible}
    w = {s: v / sum(raw.values()) * invest for s, v in raw.items()}
    for _ in range(50):
        full: set[str] = set()
        for sector, limit in sector_caps.items():
            members = [s for s in w if mkt.sector[s] == sector]
            exposure = sum(w[s] for s in members)
            if exposure >= limit - 1e-9 and members:
                full.update(members)
                if exposure > limit:
                    for s in members:
                        w[s] *= limit / exposure
        for s in w:
            if w[s] >= cap:
                w[s] = cap
                full.add(s)
        shortfall = invest - sum(w.values())
        room = [s for s in w if s not in full]
        if shortfall < 1e-6 or not room:
            break
        base = sum(w[s] for s in room)
        for s in room:
            w[s] += shortfall * w[s] / base
    return w


def _trading_day_after(mkt: Market, d: date, n: int) -> date:
    later = [x for x in mkt.days if x > d]
    return later[n - 1] if len(later) >= n else d + timedelta(days=n)


def simulate_fund(
    rng: random.Random, spec: FundSpec, mkt: Market
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Returns (cash_flows, transactions) for one fund."""
    excluded = {mkt.sec_by_code.get(r[1] or "") for r in spec.rules if r[0] == "EXCLUDE_SECURITY"}
    universe = [mkt.sec_by_code[c] for c in spec.universe if c in mkt.sec_by_code]
    universe = [s for s in universe if s not in excluded]
    days = [d for d in mkt.days if d >= spec.inception]
    if not days or not universe:
        return [], []
    flows: list[tuple[Any, ...]] = [(spec.code, days[0], money(spec.initial_sgd), "SUBSCRIPTION")]
    txns: list[tuple[Any, ...]] = []
    book = Book(cash=money(spec.initial_sgd))
    targets: dict[str, float] = {}
    last_month = None

    for i, d in enumerate(days):
        for sid, amount in mkt.divs.get(d, []):  # dividends to holders as of the day before
            units = book.qty.get(sid, 0)
            if units > 0:
                fx = mkt.fx_on(sid, d)
                cash = money(units * amount * fx)
                book.cash += cash
                txns.append((spec.code, sid, d, d + timedelta(days=30), "DIVIDEND", 0, None,
                             fx, Decimal(0), cash))  # fmt: skip

        month = (d.year, d.month)
        if month == last_month:
            continue
        last_month = month  # first trading day of the month: flows + rebalance

        available = [s for s in universe if d in mkt.px.get(s, {})]
        if i == 0 or d.month in (1, 4, 7, 10) or set(available) - set(targets):
            targets = _target_weights(rng, available, spec, mkt)  # re-tilt quarterly

        nav = book.cash + sum(
            money(q * mkt.px[s][d] * mkt.fx_on(s, d))
            for s, q in book.qty.items()
            if q and d in mkt.px[s]
        )
        if spec.monthly_flows and i > 0:
            flow = money(float(nav) * rng.uniform(-0.02, 0.03))
            flows.append((spec.code, d, flow, "SUBSCRIPTION" if flow > 0 else "REDEMPTION"))
            book.cash += flow
            nav += flow

        # Cash discipline: buys may only spend above a reserve; if cash has fallen below it
        # (redemptions, drift), ignore the tolerance band so overweight names are trimmed.
        reserve = money(float(nav) * spec.cash_target_pct / 100 / 2)
        band = 0.0 if book.cash < reserve else 0.015
        settle = _trading_day_after(mkt, d, 2)
        orders: list[tuple[str, int]] = []
        for sid in set(targets) | {s for s, q in book.qty.items() if q}:
            price = mkt.px.get(sid, {}).get(d)
            if price is None:
                continue
            fx = mkt.fx_on(sid, d)
            current = book.qty.get(sid, 0)
            target_units = float(nav) * targets.get(sid, 0.0) / (price * fx)
            drift = abs(current - target_units) * price * fx / float(nav)
            if drift < band and sid in targets:
                continue  # inside the tolerance band
            lot = mkt.board_lot[sid]
            delta = int((target_units - current) / lot) * lot
            if delta:
                orders.append((sid, delta))

        for sid, delta in sorted(orders, key=lambda o: o[1]):  # sells (negative) first
            price, fx = mkt.px[sid][d], mkt.fx_on(sid, d)
            notional = money(abs(delta) * price * fx)
            fees = max(money(notional * Decimal("0.001")), Decimal(25))
            spendable = book.cash - reserve
            if delta > 0 and spendable - notional - fees < 0:
                lot = mkt.board_lot[sid]
                delta = int(float(spendable - fees) / (price * fx) / lot) * lot
                if delta <= 0:
                    continue
                notional = money(delta * price * fx)
                fees = max(money(notional * Decimal("0.001")), Decimal(25))
            amount = -(notional + fees) if delta > 0 else notional - fees
            book.cash += amount
            book.qty[sid] = book.qty.get(sid, 0) + delta
            txns.append((spec.code, sid, d, settle, "BUY" if delta > 0 else "SELL", abs(delta),
                         Decimal(str(price)), Decimal(f"{fx:.6f}"), fees, amount))  # fmt: skip
    return flows, txns


def seed(conn: psycopg.Connection, seed_value: int = 42) -> dict[str, int]:
    rng = random.Random(seed_value)
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO users VALUES (%s, %s, %s, %s)", USERS)
        clients = make_clients(rng)
        cur.executemany(
            "INSERT INTO clients VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", clients
        )
    mkt = load_market(conn)
    counts = {"users": len(USERS), "clients": len(clients), "funds": 0, "transactions": 0}
    for spec in FUNDS:
        client_id = clients[spec.client_index][0] if spec.client_index is not None else None
        conn.execute(
            "INSERT INTO funds VALUES (%s, %s, %s, %s, %s, %s, 'SGD')",
            (spec.code, spec.name, spec.fund_type, client_id, spec.pm, spec.inception),
        )
        for rule_type, param, limit, desc in spec.rules:
            if rule_type == "EXCLUDE_SECURITY":
                param = mkt.sec_by_code.get(param or "", param)
            conn.execute(
                "INSERT INTO mandate_rules "
                "(fund_code, rule_type, rule_param, limit_value, description) "
                "VALUES (%s, %s, %s, %s, %s)",
                (spec.code, rule_type, param, limit, desc),
            )
        flows, txns = simulate_fund(rng, spec, mkt)
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO cash_flows (fund_code, flow_date, amount_sgd, flow_type) "
                "VALUES (%s, %s, %s, %s)",
                flows,
            )
            with cur.copy(
                "COPY transactions (fund_code, security_id, trade_date, settle_date, txn_type, "
                "quantity, price, fx_rate, fees_sgd, amount_sgd) FROM STDIN"
            ) as copy:
                for t in txns:
                    copy.write_row(t)
        counts["funds"] += 1
        counts["transactions"] += len(txns)

    def sid(code: str) -> str | None:
        return mkt.sec_by_code.get(code)

    restricted = [
        (sid("AJBU"), "MNPI: deal team advising the sponsor on a possible asset injection",
         "u_goh_sp", "2026-09-22 09:15:00", None),
        (sid("N2IU"), "Research blackout ahead of results", "u_goh_sp",
         "2026-03-02 08:30:00", "2026-05-15 18:00:00"),
    ]  # fmt: skip
    for row in restricted:
        if row[0]:
            conn.execute(
                "INSERT INTO restricted_list (security_id, reason, added_by, added_at, removed_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                row,
            )
    seed_orders = [
        ("HCREIT", sid("M44U"), "BUY", 200_000, "Logistics rents recovering; yield above 10y avg",
         "u_lim_jh", "PROPOSED", None, None),
        ("HCDIV", sid("C6L"), "BUY", 50_000, "Travel demand recovery", "u_nur_a", "REJECTED",
         "u_ong_bk", "Not a dividend story; outside fund style"),
    ]  # fmt: skip
    for o in seed_orders:
        if o[1]:
            conn.execute(
                "INSERT INTO orders (fund_code, security_id, side, quantity, rationale, "
                "proposed_by, status, decided_by, decision_note, decided_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "CASE WHEN %s::text IS NULL THEN NULL ELSE now() END)",
                (*o, o[7]),
            )
    return counts

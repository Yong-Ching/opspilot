# Harbourfront Capital PMS (legacy)

A **simulated existing system**: the Portfolio Management System of *Harbourfront Capital*, a fictional Singapore
asset manager. ResearchPilot must integrate with it **without changing it**, as an FDE would at a real client.

- **Market data is real:** daily prices, dividends and USD/SGD for the 25 names in `data/universe.csv` (fetched
  with `make market-data`, not committed).
- **The firm is synthetic:** 9 staff, 40 clients (KYC incl. NRIC), 2 unit trusts + 3 segregated mandates, and a
  trade history from 2021 simulated **at real closing prices** (board lots, fees, dividends on ex-dates, cash
  reserve), so holdings and weights look real. Deterministic (`--seed`).

## Run
```bash
make market-data   # ~1 min
make pms-load      # ~1 s
make pms           # API on :8100 → http://localhost:8100/docs (Authorize: dev-hc-key)
```

## Funds
| Code | Fund | PM | Notes |
|---|---|---|---|
| HCREIT | HC Singapore REIT Income Fund | u_tan_wl | 15 S-REITs; issuer ≤ 15%, hospitality ≤ 12%, REITs ≥ 90% |
| HCDIV | HC Singapore Dividend Fund | u_ong_bk | Blue chips + REITs; banks ≤ 45%; excludes Wilmar (ESG) |
| MND-001…003 | Segregated client mandates | u_chua_m | Conservative / balanced / growth, each with its own limits |

## Users
Analysts `u_lim_jh`, `u_raj_k`, `u_nur_a` · PMs `u_tan_wl`, `u_ong_bk`, `u_chua_m` · Compliance `u_goh_sp` · RMs `u_ng_d`, `u_farah_i`

## API (header `X-HC-ApiKey: dev-hc-key`)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/securities`, `/securities/{id}`, `/securities/lookup?code=` | Lookup accepts SGX or Yahoo codes, **including retired ones** (J91U → ESR-REIT) |
| GET | `/api/v1/securities/{id}/prices?dt_from&dt_to` | Prices in **cents** |
| GET | `/api/v1/funds`, `/funds/{code}` | |
| GET | `/api/v1/funds/{code}/holdings?as_of=` | NAV, cash, positions with weights |
| GET | `/api/v1/funds/{code}/exposure?by=sector\|issuer\|type` | |
| GET | `/api/v1/funds/{code}/mandate` | Rules are stored but **not enforced** by the PMS |
| GET | `/api/v1/funds/{code}/transactions` | Old settlement module: `TxnRef`, `TradeDt`, `AmtSGD`… |
| GET | `/api/v1/clients`, `/clients/{id}` | Returns the **full NRIC** to any caller with the key |
| GET | `/api/v1/restricted-list`, `/restricted-list/check?security_id=` | Check never returns the reason |
| POST | `/api/v1/restricted-list`, `/restricted-list/{id}/remove` | Compliance only |
| GET | `/api/v1/orders`, `/orders/{id}` | |
| POST | `/api/v1/orders` | Propose (analyst/PM). Enforces board lots, restricted list, holdings |
| POST | `/api/v1/orders/{id}/approve` · `/reject` | Fund's PM only; approver ≠ proposer (**four-eyes**); reject needs a note |
| POST | `/api/v1/orders/{id}/execute` | Simulated dealing desk: fills at the latest close |

## Known quirks and gaps (deliberate: ResearchPilot has to handle them)
- **Business errors return HTTP 200** with `{"success": false, "error_code": "ERR_..."}`; auth errors are 401 `{"detail": ...}`.
- **Dates** are `DD/MM/YYYY`; **prices in cents**, cash in SGD dollars, dividends per unit in dollars.
- **Internal security IDs** (`HC000121`) differ from tickers; tickers change over time.
- **`Y`/`N` flags** instead of booleans; **page size silently capped** at 50.
- **Identity is trusted, not verified:** one shared API key; the caller says who is acting (`proposed_by`, `user_id`).
- **Mandate limits are not enforced** (only the restricted list is): pre-trade compliance is ResearchPilot's job.
- **Client records expose full NRIC**: ResearchPilot must mask before anything reaches an LLM or a screen.

## Events (transactional outbox)
`order.proposed`, `order.approved`, `order.rejected`, `order.executed`, `restricted_list.updated` are recorded in
the `outbox` table in the same transaction as the change, then delivered to `HC_WEBHOOK_URLS` by the dispatcher
(`uv run python -m hc_pms.outbox`).

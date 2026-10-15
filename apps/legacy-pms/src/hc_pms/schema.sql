-- Harbourfront Capital PMS schema (legacy system, simulated).
-- Amounts: prices are stored in MINOR UNITS (cents) of the security's currency; cash in SGD.

CREATE TABLE IF NOT EXISTS users (
    user_id   TEXT PRIMARY KEY,               -- e.g. 'u_tan_wl'
    full_name TEXT NOT NULL,
    role      TEXT NOT NULL CHECK (role IN ('ANALYST', 'PM', 'COMPLIANCE', 'RM')),
    team      TEXT NOT NULL                   -- 'RESEARCH', 'PORTFOLIO', 'COMPLIANCE', 'WEALTH'
);

CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,             -- internal ID, e.g. 'HC000014' (NOT the ticker)
    sec_name    TEXT NOT NULL,
    sec_type    TEXT NOT NULL CHECK (sec_type IN ('REIT', 'EQUITY')),
    sector      TEXT NOT NULL,
    currency    TEXT NOT NULL,
    board_lot   INT  NOT NULL DEFAULT 100,
    sponsor     TEXT
);

-- Tickers change (e.g. ESR-REIT J91U -> 9A4U), so identifiers live in their own table.
CREATE TABLE IF NOT EXISTS security_identifiers (
    security_id TEXT NOT NULL REFERENCES securities,
    id_type     TEXT NOT NULL CHECK (id_type IN ('SGX', 'YAHOO')),
    id_value    TEXT NOT NULL,
    is_current  BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_type, id_value)
);

CREATE TABLE IF NOT EXISTS prices (
    security_id TEXT NOT NULL REFERENCES securities,
    px_date     DATE NOT NULL,
    px_close_minor BIGINT NOT NULL,          -- cents of the security's currency
    PRIMARY KEY (security_id, px_date)
);

CREATE TABLE IF NOT EXISTS dividends (
    security_id TEXT NOT NULL REFERENCES securities,
    ex_date     DATE NOT NULL,
    amount      NUMERIC(14, 6) NOT NULL,      -- per unit, security currency (NOT cents: inconsistent on purpose)
    PRIMARY KEY (security_id, ex_date)
);

CREATE TABLE IF NOT EXISTS fx_rates (
    ccy         TEXT NOT NULL,
    fx_date     DATE NOT NULL,
    rate_to_sgd NUMERIC(14, 6) NOT NULL,
    PRIMARY KEY (ccy, fx_date)
);

CREATE TABLE IF NOT EXISTS clients (
    client_id     TEXT PRIMARY KEY,           -- e.g. 'C00017'
    full_name     TEXT NOT NULL,
    nric          TEXT NOT NULL,              -- full NRIC/FIN stored and returned by the API (legacy!)
    date_of_birth DATE NOT NULL,
    email         TEXT NOT NULL,
    mobile        TEXT NOT NULL,              -- +65 9xxx xxxx
    address       TEXT NOT NULL,
    risk_profile  TEXT NOT NULL CHECK (risk_profile IN ('CONSERVATIVE', 'BALANCED', 'GROWTH')),
    rm_user_id    TEXT NOT NULL REFERENCES users,
    kyc_date      DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS funds (
    fund_code      TEXT PRIMARY KEY,          -- e.g. 'HCREIT'
    fund_name      TEXT NOT NULL,
    fund_type      TEXT NOT NULL CHECK (fund_type IN ('UNIT_TRUST', 'MANDATE')),
    client_id      TEXT REFERENCES clients,   -- set for segregated mandates
    pm_user_id     TEXT NOT NULL REFERENCES users,
    inception_date DATE NOT NULL,
    base_ccy       TEXT NOT NULL DEFAULT 'SGD'
);

-- Investment restrictions. The legacy PMS stores them but only enforces the restricted list.
CREATE TABLE IF NOT EXISTS mandate_rules (
    rule_id     BIGSERIAL PRIMARY KEY,
    fund_code   TEXT NOT NULL REFERENCES funds,
    rule_type   TEXT NOT NULL CHECK (rule_type IN
                  ('MAX_ISSUER_PCT', 'MAX_SECTOR_PCT', 'MIN_CASH_PCT', 'MIN_REIT_PCT', 'EXCLUDE_SECURITY')),
    rule_param  TEXT,                         -- sector name or security_id, depending on rule_type
    limit_value NUMERIC(6, 2),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash_flows (
    flow_id    BIGSERIAL PRIMARY KEY,
    fund_code  TEXT NOT NULL REFERENCES funds,
    flow_date  DATE NOT NULL,
    amount_sgd NUMERIC(16, 2) NOT NULL,       -- + subscription, - redemption
    flow_type  TEXT NOT NULL CHECK (flow_type IN ('SUBSCRIPTION', 'REDEMPTION'))
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id      BIGSERIAL PRIMARY KEY,
    fund_code   TEXT NOT NULL REFERENCES funds,
    security_id TEXT NOT NULL REFERENCES securities,
    trade_date  DATE NOT NULL,
    settle_date DATE NOT NULL,
    txn_type    TEXT NOT NULL CHECK (txn_type IN ('BUY', 'SELL', 'DIVIDEND')),
    quantity    BIGINT NOT NULL,              -- units; 0 for DIVIDEND
    price       NUMERIC(14, 6),               -- security currency, NULL for DIVIDEND
    fx_rate     NUMERIC(14, 6) NOT NULL,      -- to SGD on trade date
    fees_sgd    NUMERIC(14, 2) NOT NULL DEFAULT 0,
    amount_sgd  NUMERIC(16, 2) NOT NULL,      -- cash impact: BUY < 0, SELL/DIVIDEND > 0
    order_id    BIGINT                        -- set when created from an executed order
);

CREATE TABLE IF NOT EXISTS restricted_list (
    entry_id    BIGSERIAL PRIMARY KEY,
    security_id TEXT NOT NULL REFERENCES securities,
    reason      TEXT NOT NULL,
    added_by    TEXT NOT NULL REFERENCES users,
    added_at    TIMESTAMP NOT NULL DEFAULT now(),
    removed_at  TIMESTAMP                     -- NULL = currently restricted
);

CREATE TABLE IF NOT EXISTS orders (
    order_id       BIGSERIAL PRIMARY KEY,
    fund_code      TEXT NOT NULL REFERENCES funds,
    security_id    TEXT NOT NULL REFERENCES securities,
    side           TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity       BIGINT NOT NULL CHECK (quantity > 0),
    limit_price    NUMERIC(14, 6),
    rationale      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'PROPOSED'
                     CHECK (status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'EXECUTED', 'CANCELLED')),
    proposed_by    TEXT NOT NULL REFERENCES users,
    proposed_at    TIMESTAMP NOT NULL DEFAULT now(),
    decided_by     TEXT REFERENCES users,
    decided_at     TIMESTAMP,
    decision_note  TEXT
);

-- Transactional outbox: events are written in the SAME transaction as the business change,
-- then a separate dispatcher delivers them to webhook subscribers. (Phase 1: yours.)
CREATE TABLE IF NOT EXISTS outbox (
    id           BIGSERIAL PRIMARY KEY,
    event_type   TEXT NOT NULL,            -- e.g. 'order.proposed', 'order.approved'
    aggregate_id TEXT NOT NULL,            -- the order_id / entry_id the event is about
    payload      JSONB NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT now(),
    published_at TIMESTAMP,                -- NULL = not delivered yet
    attempts     INT NOT NULL DEFAULT 0,
    last_error   TEXT
);

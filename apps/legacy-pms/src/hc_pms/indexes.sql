CREATE INDEX IF NOT EXISTS ix_identifiers_security ON security_identifiers (security_id);
CREATE INDEX IF NOT EXISTS ix_prices_date ON prices (px_date);
CREATE INDEX IF NOT EXISTS ix_txn_fund_date ON transactions (fund_code, trade_date);
CREATE INDEX IF NOT EXISTS ix_txn_fund_security ON transactions (fund_code, security_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status, fund_code);
CREATE INDEX IF NOT EXISTS ix_restricted_active ON restricted_list (security_id) WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_outbox_unpublished ON outbox (id) WHERE published_at IS NULL;

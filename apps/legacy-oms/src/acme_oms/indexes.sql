CREATE INDEX IF NOT EXISTS ix_customers_unique ON customers (customer_unique_id);
CREATE INDEX IF NOT EXISTS ix_orders_customer ON orders (customer_id);
CREATE INDEX IF NOT EXISTS ix_orders_status_purchase ON orders (order_status, order_purchase_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_orders_purchase ON orders (order_purchase_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_items_seller ON order_items (seller_id);
CREATE INDEX IF NOT EXISTS ix_reviews_order ON order_reviews (order_id);
CREATE INDEX IF NOT EXISTS ix_refunds_order ON refund_requests (order_id);
CREATE INDEX IF NOT EXISTS ix_outbox_unpublished ON outbox (id) WHERE published_at IS NULL;

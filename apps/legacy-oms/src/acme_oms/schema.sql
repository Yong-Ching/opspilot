-- Acme Market OMS schema. Column names are kept exactly as in the source system,
-- including its typos (product_name_lenght) and Portuguese category names.

CREATE TABLE IF NOT EXISTS customers (
    customer_id              TEXT PRIMARY KEY,   -- NOTE: one per ORDER, not per person
    customer_unique_id       TEXT NOT NULL,      -- the real person
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id              TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city            TEXT,
    seller_state           TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id                 TEXT PRIMARY KEY,
    product_category_name      TEXT,
    product_name_lenght        INT,
    product_description_lenght INT,
    product_photos_qty         INT,
    product_weight_g           INT,
    product_length_cm          INT,
    product_height_cm          INT,
    product_width_cm           INT
);

CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name         TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id                      TEXT PRIMARY KEY,
    customer_id                   TEXT NOT NULL REFERENCES customers,
    order_status                  TEXT NOT NULL,
    order_purchase_timestamp      TIMESTAMP,
    order_approved_at             TIMESTAMP,
    order_delivered_carrier_date  TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id            TEXT NOT NULL REFERENCES orders,
    order_item_id       INT  NOT NULL,
    product_id          TEXT NOT NULL REFERENCES products,
    seller_id           TEXT NOT NULL REFERENCES sellers,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10, 2),
    freight_value       NUMERIC(10, 2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS order_payments (
    order_id             TEXT NOT NULL REFERENCES orders,
    payment_sequential   INT  NOT NULL,
    payment_type         TEXT,
    payment_installments INT,
    payment_value        NUMERIC(10, 2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS order_reviews (
    id                      BIGSERIAL PRIMARY KEY, -- source review_id is not unique
    review_id               TEXT NOT NULL,
    order_id                TEXT NOT NULL REFERENCES orders,
    review_score            INT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

-- Added by Acme for the refund workflow (not in the Olist source data).
CREATE TABLE IF NOT EXISTS refund_requests (
    refund_id    BIGSERIAL PRIMARY KEY,
    order_id     TEXT NOT NULL REFERENCES orders,
    amount       NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    reason       TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at   TIMESTAMP NOT NULL DEFAULT now()
);

-- Transactional outbox: events are written in the SAME transaction as the business change,
-- then a separate dispatcher delivers them to webhook subscribers. (Phase 1, step 3: yours.)
CREATE TABLE IF NOT EXISTS outbox (
    id           BIGSERIAL PRIMARY KEY,
    event_type   TEXT NOT NULL,            -- e.g. 'refund.requested', 'order.updated'
    aggregate_id TEXT NOT NULL,            -- the order_id / refund_id the event is about
    payload      JSONB NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT now(),
    published_at TIMESTAMP,                -- NULL = not delivered yet
    attempts     INT NOT NULL DEFAULT 0,
    last_error   TEXT
);

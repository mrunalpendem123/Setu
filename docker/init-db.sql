CREATE DATABASE indus;
CREATE DATABASE merchant;
CREATE DATABASE psp;

\connect indus

CREATE TABLE IF NOT EXISTS indus_merchants (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    base_url VARCHAR NOT NULL,
    product_feed_url VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

\connect psp

CREATE TABLE IF NOT EXISTS delegated_payment_tokens (
    token_id VARCHAR PRIMARY KEY,
    max_amount INTEGER NOT NULL,
    currency VARCHAR NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS psp_idempotency_keys (
    key VARCHAR PRIMARY KEY,
    request_hash VARCHAR NOT NULL,
    response_body JSONB NOT NULL,
    status_code INTEGER NOT NULL
);

-- ─────────────────────────────────────────────
-- Customer Tiers
-- ─────────────────────────────────────────────
CREATE TABLE customer_tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- Organisations
-- ─────────────────────────────────────────────
CREATE TABLE organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    domain VARCHAR(100),
    customer_tier_id INTEGER REFERENCES customer_tiers(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_organisations_domain UNIQUE (domain)
);

-- ─────────────────────────────────────────────
-- Roles
-- ─────────────────────────────────────────────
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
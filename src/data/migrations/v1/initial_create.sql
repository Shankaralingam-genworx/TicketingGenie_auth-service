-- =============================================================================
-- Migration  : V1__create_auth_schema.sql
-- Service    : Auth Service
-- Schema     : auth
-- Database   : Shared DB (auth + ticket services)
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- SCHEMA
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;

-- ---------------------------------------------------------------------------
-- ENUM TYPES  (scoped to auth schema)
-- ---------------------------------------------------------------------------

CREATE TYPE auth.customertier AS ENUM (
    'smb',
    'enterprise'
);

CREATE TYPE auth.preferredcontact AS ENUM (
    'email',
    'portal'
);

-- ---------------------------------------------------------------------------
-- TABLE: auth.roles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.roles (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(50)  NOT NULL UNIQUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- TABLE: auth.users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.users (
    id            SERIAL        PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    password_hash VARCHAR       NOT NULL,
    role_id       INTEGER       NOT NULL REFERENCES auth.roles(id),
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users (email);

-- ---------------------------------------------------------------------------
-- TABLE: auth.customers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.customers (
    id                SERIAL                PRIMARY KEY,
    user_id           INTEGER               NOT NULL UNIQUE REFERENCES auth.users(id),
    phone             VARCHAR(20),
    preferred_contact auth.preferredcontact,
    customer_tier     auth.customertier     NOT NULL DEFAULT 'smb'
);

-- ---------------------------------------------------------------------------
-- TABLE: auth.refresh_tokens
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    id         SERIAL        PRIMARY KEY,
    user_id    INTEGER       NOT NULL REFERENCES auth.users(id),
    token      VARCHAR       NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ   NOT NULL,
    revoked    BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON auth.refresh_tokens (token);

-- ---------------------------------------------------------------------------
-- TABLE: auth.teams
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.teams (
    id           SERIAL        PRIMARY KEY,
    name         VARCHAR(100)  NOT NULL UNIQUE,
    team_lead_id INTEGER       NOT NULL REFERENCES auth.users(id),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- TABLE: auth.team_members
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.team_members (
    id         SERIAL       PRIMARY KEY,
    team_id    INTEGER      NOT NULL REFERENCES auth.teams(id),
    user_id    INTEGER      NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_team_user UNIQUE (team_id, user_id)
);

COMMIT;
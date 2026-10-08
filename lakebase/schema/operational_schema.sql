-- ============================================================================
-- Operational (WRITABLE) Postgres schema — TelcoABC Retention Command Center
-- ----------------------------------------------------------------------------
-- The governed Unity Catalog table (gold_churn_risk_scores) is synced into
-- Lakebase READ-ONLY as `public.synced_churn_risk_scores`. Application state and
-- actions must live in separate WRITABLE tables — that is this `ops` schema.
--
-- Domain: telco customer retention. Related tables + keys (not a flat dump),
-- and `ops.case_notes.note_text` is the searchable text field for Lakebase Search.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS ops;

-- Retention agents handling save cases
CREATE TABLE IF NOT EXISTS ops.agents (
    agent_id    text PRIMARY KEY,
    agent_name  text NOT NULL,
    team        text,
    tier        text
);

-- One retention case per at-risk customer engagement.
-- customer_id joins to the synced (read-only) UC risk-score table.
CREATE TABLE IF NOT EXISTS ops.retention_cases (
    case_id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id           text NOT NULL,
    market                text,
    competitor_id         text,                       -- competitor threatening the account
    assigned_agent_id     text REFERENCES ops.agents(agent_id),
    status                text NOT NULL DEFAULT 'Open'   -- Open / In Progress / Saved / Churned
                          CHECK (status IN ('Open','In Progress','Saved','Churned')),
    priority              text NOT NULL DEFAULT 'Medium'
                          CHECK (priority IN ('Low','Medium','High','Critical')),
    recommended_offer_id  text,
    opened_at             timestamptz NOT NULL DEFAULT now(),
    closed_at             timestamptz,
    updated_at            timestamptz NOT NULL DEFAULT now()
);

-- Free-text agent notes on a case — the SEARCHABLE text column.
CREATE TABLE IF NOT EXISTS ops.case_notes (
    note_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id     bigint NOT NULL REFERENCES ops.retention_cases(case_id) ON DELETE CASCADE,
    agent_id    text REFERENCES ops.agents(agent_id),
    note_text   text NOT NULL,                         -- <-- Lakebase Search target
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Save offers presented during a case (actions taken).
CREATE TABLE IF NOT EXISTS ops.offers_presented (
    offer_presentation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id       bigint NOT NULL REFERENCES ops.retention_cases(case_id) ON DELETE CASCADE,
    offer_id      text NOT NULL,
    offer_name    text,
    presented_at  timestamptz NOT NULL DEFAULT now(),
    accepted      boolean
);

CREATE INDEX IF NOT EXISTS idx_cases_customer ON ops.retention_cases (customer_id);
CREATE INDEX IF NOT EXISTS idx_cases_status   ON ops.retention_cases (status);
CREATE INDEX IF NOT EXISTS idx_notes_case     ON ops.case_notes (case_id);
CREATE INDEX IF NOT EXISTS idx_offers_case    ON ops.offers_presented (case_id);

-- Reverse Lakehouse Sync (Lakebase CDF) requires full row images so UPDATE/DELETE
-- carry before/after state into the UC SCD2 history table.
ALTER TABLE ops.retention_cases  REPLICA IDENTITY FULL;
ALTER TABLE ops.case_notes       REPLICA IDENTITY FULL;
ALTER TABLE ops.offers_presented REPLICA IDENTITY FULL;

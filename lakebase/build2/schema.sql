-- ============================================================================
-- Build 2 — app state & actions (WRITABLE Postgres; never touches the read-only
-- synced UC table telcoabc_retention.synced_churn_risk_scores).
-- ============================================================================

-- Workflow state / observability: trigger events + recorded decisions, timestamped.
CREATE TABLE IF NOT EXISTS ops.workflow_events (
    event_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type      text NOT NULL,        -- view_refresh_trigger | flagged | explanation | whatif | draft
                                          -- | action_proposed | action_approved | action_committed
    trigger_source  text,                 -- schedule | system_update | user
    entity_type     text,                 -- customer | case | action
    entity_id       text,
    actor           text,                 -- system | assistant | <user email>
    detail          jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Writeback action table with human-in-the-loop approval.
CREATE TABLE IF NOT EXISTS ops.retention_actions (
    action_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id           bigint REFERENCES ops.retention_cases(case_id),
    customer_id       text NOT NULL,
    action_type       text NOT NULL DEFAULT 'present_offer',
    proposed_offer_id text,
    proposed_by       text NOT NULL DEFAULT 'system',
    rationale         text,
    approval_status   text NOT NULL DEFAULT 'proposed'
                      CHECK (approval_status IN ('proposed','approved','corrected','rejected')),
    approver          text,
    final_offer_id    text,               -- set on approve/correct
    created_at        timestamptz NOT NULL DEFAULT now(),
    committed_at      timestamptz         -- set when the decision commits (closed loop)
);

CREATE INDEX IF NOT EXISTS idx_actions_case   ON ops.retention_actions (case_id);
CREATE INDEX IF NOT EXISTS idx_events_entity  ON ops.workflow_events (entity_type, entity_id);

ALTER TABLE ops.workflow_events   REPLICA IDENTITY FULL;
ALTER TABLE ops.retention_actions REPLICA IDENTITY FULL;

-- Ranked / flagged live worklist: the decision surface. A committed action removes
-- the flag on the next read (closed loop).
CREATE OR REPLACE VIEW ops.v_retention_worklist AS
SELECT
    s.customer_id,
    s.market,
    ROUND(s.churn_score::numeric, 4)                       AS churn_score,
    s.risk_tier,
    c.case_id,
    c.competitor_id,
    c.recommended_offer_id,
    c.status,
    (act.action_id IS NULL)                                AS needs_action,   -- FLAG
    RANK() OVER (ORDER BY s.churn_score DESC)              AS priority_rank
FROM telcoabc_retention.synced_churn_risk_scores s
JOIN ops.retention_cases c ON c.customer_id = s.customer_id
LEFT JOIN ops.retention_actions act
       ON act.case_id = c.case_id AND act.committed_at IS NOT NULL
WHERE s.risk_tier = 'Critical' AND c.status IN ('Open','In Progress')
ORDER BY needs_action DESC, s.churn_score DESC;

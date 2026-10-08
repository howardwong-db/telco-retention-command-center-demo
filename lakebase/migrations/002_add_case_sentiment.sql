-- 002_add_case_sentiment.sql
-- Agentic change (authored by the Claude coding agent): add a rule-based `sentiment`
-- signal to retention case notes so leads can triage the highest-intent (angriest)
-- notes first. This is a schema + data change, tested on the Lakebase `dev` branch,
-- validated, then promoted to `production`.
ALTER TABLE ops.case_notes ADD COLUMN IF NOT EXISTS sentiment text;

UPDATE ops.case_notes
SET sentiment = CASE
    WHEN note_text ~* '(cancel|switch|threaten|port out|leave|walk|disconnect)' THEN 'negative'
    WHEN note_text ~* '(loyal|considering|open to|match|promo)'                  THEN 'at_risk'
    ELSE 'neutral'
END;

CREATE INDEX IF NOT EXISTS idx_notes_sentiment ON ops.case_notes (sentiment);

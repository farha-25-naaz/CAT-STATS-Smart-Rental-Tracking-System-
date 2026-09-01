-- Phase 2 schema changes. Run in the Supabase SQL editor before using /ingest/*.

-- 1. Maintenance risk (one row per asset, upserted by /ingest/risk)
CREATE TABLE IF NOT EXISTS maintenance_risk (
  asset_id VARCHAR(20) PRIMARY KEY REFERENCES assets(asset_id),
  risk_score FLOAT,
  risk_tier VARCHAR(20),
  predicted_failure_window_days INT,
  contributing_factors JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. NL summary attached to an alert (/ingest/summary, when a matching alert exists)
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS summary TEXT;

-- 3. Fallback log for summaries with no matching alert (/ingest/summary)
CREATE TABLE IF NOT EXISTS summaries (
  summary_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  asset_id VARCHAR(20) REFERENCES assets(asset_id),
  summary TEXT NOT NULL,
  severity VARCHAR(20),
  generated_at TIMESTAMPTZ DEFAULT NOW()
);

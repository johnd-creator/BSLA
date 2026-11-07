-- Additive local evidence only. No source/WO/cursor/registry rewrite.
CREATE TABLE IF NOT EXISTS asset_reference_check (
    asset_id VARCHAR(60) PRIMARY KEY,
    outcome VARCHAR(40) NOT NULL,
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    retry_after TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_asset_reference_check_retry_after
    ON asset_reference_check (retry_after);

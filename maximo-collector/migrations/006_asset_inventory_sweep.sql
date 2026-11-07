-- Additive private keyset staging/checkpoint tables, existing Maximo DB only.
CREATE TABLE IF NOT EXISTS asset_inventory_sweep (
 id varchar(36) PRIMARY KEY, reference_sha varchar(64) NOT NULL,
 state varchar(24) NOT NULL, upper_id bigint NOT NULL DEFAULT 0,
 collect_cursor bigint NOT NULL DEFAULT 0, verify_cursor bigint NOT NULL DEFAULT 0, delta_cursor bigint NOT NULL DEFAULT 0,
 requests integer NOT NULL DEFAULT 0, rounds integer NOT NULL DEFAULT 1,
 started_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
 result jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS asset_inventory_stage (
 sweep_id varchar(36) NOT NULL, assetid bigint NOT NULL, assetnum varchar(60) NOT NULL,
 payload jsonb NOT NULL, signature varchar(64) NOT NULL, verified boolean NOT NULL DEFAULT false,
 PRIMARY KEY(sweep_id,assetid), CONSTRAINT uq_inventory_sweep_source_identity UNIQUE(sweep_id,assetnum)
);

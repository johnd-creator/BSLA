-- Additive hierarchy inventory evidence in the existing Maximo Collector database.
-- No Registry expansion, identity rewrites, deletion, or cursor changes.
CREATE TABLE IF NOT EXISTS asset_inventory (
 asset_id varchar(60) PRIMARY KEY, category varchar(20) NOT NULL,
 scope_basis varchar(40) NOT NULL, active boolean NOT NULL DEFAULT true,
 evidence jsonb NOT NULL, assessed_at timestamptz NOT NULL, source_observed_at timestamptz
);
CREATE TABLE IF NOT EXISTS asset_inventory_scan (
 id serial PRIMARY KEY, started_at timestamptz NOT NULL,
 finished_at timestamptz NOT NULL, result jsonb NOT NULL
);
-- Existing read-only Mart service can read only these new inventory relations.
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nadi_mart_reader') THEN
  GRANT SELECT ON asset_inventory, asset_inventory_scan TO nadi_mart_reader;
 END IF;
END $$;

-- B1 candidate ONLY. No runtime/CLI auto-application. Owner: Maximo/Mart.
-- Additive; deployed migrations 001-003 remain unchanged.
BEGIN;
CREATE TABLE mart_capture_domain (
 domain VARCHAR(40) PRIMARY KEY CHECK (domain IN ('asset_master','maintenance_event')),
 fence BIGINT NOT NULL CHECK (fence > 0), owner VARCHAR(36) NOT NULL,
 lease_until TIMESTAMPTZ NOT NULL, latest_run VARCHAR(36),
 last_complete_run VARCHAR(36), last_complete_at TIMESTAMPTZ
);
CREATE TABLE mart_capture_run (
 id VARCHAR(36) PRIMARY KEY, manifest_id VARCHAR(36) NOT NULL UNIQUE,
 domain VARCHAR(40) NOT NULL REFERENCES mart_capture_domain(domain),
 epoch VARCHAR(64) NOT NULL, scope JSONB NOT NULL, sealed BOOLEAN NOT NULL,
 item_count INTEGER NOT NULL CHECK (item_count >= 0),
 byte_count BIGINT NOT NULL CHECK (byte_count >= 0), manifest_digest VARCHAR(64),
 snapshot TEXT, continuation INTEGER NOT NULL CHECK (continuation BETWEEN 0 AND item_count),
 status VARCHAR(20) NOT NULL CHECK (status IN ('CAPTURING','SEALED','PARTIAL','COMPLETE','FAILED')),
 started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ,
 CHECK (NOT sealed OR (manifest_digest IS NOT NULL AND snapshot IS NOT NULL)),
 CHECK (status <> 'COMPLETE' OR (sealed AND continuation = item_count AND completed_at IS NOT NULL))
);
CREATE TABLE mart_capture_item (
 run_id VARCHAR(36) NOT NULL REFERENCES mart_capture_run(id),
 ordinal INTEGER NOT NULL CHECK (ordinal > 0), source_id VARCHAR(60) NOT NULL,
 fingerprint VARCHAR(64) NOT NULL, payload JSONB NOT NULL,
 disposition VARCHAR(30) CHECK (disposition IN ('PROJECTED','UNCHANGED','EXPECTED_EXCLUSION','DEFERRED','FAILED')),
 reason VARCHAR(40), acked_at TIMESTAMPTZ, target_id VARCHAR(200), target_digest VARCHAR(64),
 PRIMARY KEY (run_id, ordinal), UNIQUE (run_id, source_id),
 CHECK ((disposition IS NULL) = (acked_at IS NULL)),
 CHECK (disposition NOT IN ('PROJECTED','UNCHANGED') OR (target_id IS NOT NULL AND target_digest IS NOT NULL))
);
CREATE TABLE mart_capture_target (
 domain VARCHAR(40) NOT NULL, canonical_id VARCHAR(200) NOT NULL,
 fence BIGINT NOT NULL, run_id VARCHAR(36) NOT NULL REFERENCES mart_capture_run(id),
 fingerprint VARCHAR(64) NOT NULL, target_digest VARCHAR(64) NOT NULL,
 PRIMARY KEY (domain, canonical_id)
);
-- Serialize item changes with sealing; sealed membership/input and receipts are immutable.
CREATE FUNCTION mart_capture_item_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE is_sealed BOOLEAN;
BEGIN
 IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'capture evidence is append-only'; END IF;
 SELECT sealed INTO is_sealed FROM mart_capture_run WHERE id = NEW.run_id FOR UPDATE;
 IF TG_OP = 'INSERT' AND is_sealed THEN RAISE EXCEPTION 'manifest is sealed'; END IF;
 IF TG_OP = 'UPDATE' THEN
  IF ROW(NEW.run_id,NEW.ordinal,NEW.source_id,NEW.fingerprint,NEW.payload)
     IS DISTINCT FROM ROW(OLD.run_id,OLD.ordinal,OLD.source_id,OLD.fingerprint,OLD.payload)
     OR OLD.disposition IS NOT NULL OR NOT is_sealed THEN
   RAISE EXCEPTION 'immutable capture input or receipt';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mart_capture_item_guard BEFORE INSERT OR UPDATE OR DELETE ON mart_capture_item
 FOR EACH ROW EXECUTE FUNCTION mart_capture_item_guard();
CREATE FUNCTION mart_capture_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'capture evidence is append-only'; END IF;
 IF OLD.sealed AND ROW(NEW.id,NEW.manifest_id,NEW.domain,NEW.epoch,NEW.scope,NEW.sealed,
      NEW.item_count,NEW.byte_count,NEW.manifest_digest,NEW.snapshot,NEW.started_at)
    IS DISTINCT FROM ROW(OLD.id,OLD.manifest_id,OLD.domain,OLD.epoch,OLD.scope,OLD.sealed,
      OLD.item_count,OLD.byte_count,OLD.manifest_digest,OLD.snapshot,OLD.started_at) THEN
  RAISE EXCEPTION 'immutable sealed manifest';
 END IF;
 IF NEW.continuation < OLD.continuation OR EXISTS (
   SELECT 1 FROM generate_series(1,NEW.continuation) n
   LEFT JOIN mart_capture_item i ON i.run_id = NEW.id AND i.ordinal = n
   WHERE i.acked_at IS NULL
 ) THEN RAISE EXCEPTION 'continuation exceeds receipts'; END IF;
 IF NEW.status = 'COMPLETE' AND EXISTS (
   SELECT 1 FROM mart_capture_item WHERE run_id = NEW.id
   AND (disposition IS NULL OR disposition NOT IN ('PROJECTED','UNCHANGED','EXPECTED_EXCLUSION'))
 ) THEN RAISE EXCEPTION 'unresolved coverage'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mart_capture_run_guard BEFORE UPDATE OR DELETE ON mart_capture_run
 FOR EACH ROW EXECUTE FUNCTION mart_capture_run_guard();
COMMIT;

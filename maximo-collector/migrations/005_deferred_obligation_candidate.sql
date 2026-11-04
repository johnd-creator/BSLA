-- B2 candidate only. Requires reviewed B1 004; no startup application.
BEGIN;
CREATE TABLE mart_deferred_family (
 id VARCHAR(64) PRIMARY KEY, domain VARCHAR(40) NOT NULL REFERENCES mart_capture_domain(domain),
 source_system VARCHAR(16) NOT NULL, source_object VARCHAR(30) NOT NULL, source_id VARCHAR(60) NOT NULL,
 scope_key VARCHAR(40) NOT NULL, policy_epoch VARCHAR(64) NOT NULL, mapper_epoch VARCHAR(64) NOT NULL,
 current_id VARCHAR(36),
 CONSTRAINT deferred_source CHECK (source_system='MAXIMO' AND
  ((domain='asset_master' AND source_object='MXASSET') OR (domain='maintenance_event' AND source_object='MXWODETAIL'))),
 CONSTRAINT deferred_identity UNIQUE (domain,source_system,source_object,source_id,scope_key,policy_epoch,mapper_epoch)
);
CREATE TABLE mart_deferred_version (
 id VARCHAR(36) PRIMARY KEY, family_id VARCHAR(64) NOT NULL REFERENCES mart_deferred_family(id),
 version INTEGER NOT NULL, fingerprint VARCHAR(64) NOT NULL,
 first_run VARCHAR(36) NOT NULL, first_manifest VARCHAR(36) NOT NULL REFERENCES mart_capture_run(manifest_id),
 first_ordinal INTEGER NOT NULL, predecessor_id VARCHAR(36) REFERENCES mart_deferred_version(id), scope_proof VARCHAR(16) NOT NULL, site VARCHAR(20), organization VARCHAR(20),
 canonical_id VARCHAR(200), classification VARCHAR(40) NOT NULL, reason VARCHAR(40) NOT NULL,
 state VARCHAR(32) NOT NULL, first_at TIMESTAMPTZ NOT NULL, last_attempt TIMESTAMPTZ NOT NULL,
 attempts INTEGER NOT NULL, revision INTEGER NOT NULL, last_event VARCHAR(36), resolution_event VARCHAR(36),
 superseded_by VARCHAR(36) REFERENCES mart_deferred_version(id) DEFERRABLE INITIALLY DEFERRED,
 fence BIGINT NOT NULL, owner VARCHAR(36) NOT NULL,
 CONSTRAINT deferred_version_identity UNIQUE (family_id,version),
 CONSTRAINT deferred_input FOREIGN KEY(first_run,first_ordinal) REFERENCES mart_capture_item(run_id,ordinal),
 CONSTRAINT deferred_scope CHECK ((scope_proof='PROVEN' AND site='BSR' AND organization='IP') OR
  (scope_proof='UNKNOWN' AND site IS NULL AND organization IS NULL)),
 CONSTRAINT deferred_state CHECK (state IN ('OPEN','ELIGIBLE_FOR_RETRY','BLOCKED_NEEDS_REVIEW','SUPERSEDED_BY_NEW_VERSION','RESOLVED')),
 CONSTRAINT deferred_class CHECK (classification IN ('DEFERRED_DEPENDENCY','DEFERRED_SCOPE_PROOF','DEFERRED_MAPPING','FAILED_MAPPING','RESOLUTION_PENDING')),
 CONSTRAINT deferred_reason CHECK (reason IN ('MISSING_LOCAL_EQUIPMENT','UNPROVEN_SCOPE','MISSING_REQUIRED_ID','INVALID_MAPPING','RECEIPT_RECONCILIATION')),
 CONSTRAINT deferred_counts CHECK (version>0 AND attempts>=0 AND revision>0),
 CONSTRAINT deferred_closed_proof CHECK ((state<>'RESOLVED' OR resolution_event IS NOT NULL) AND
  (state<>'SUPERSEDED_BY_NEW_VERSION' OR superseded_by IS NOT NULL))
);
ALTER TABLE mart_deferred_family ADD CONSTRAINT deferred_current
 FOREIGN KEY(current_id) REFERENCES mart_deferred_version(id) DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX deferred_one_active ON mart_deferred_version(family_id)
 WHERE state IN ('OPEN','ELIGIBLE_FOR_RETRY','BLOCKED_NEEDS_REVIEW');
CREATE INDEX deferred_family_state ON mart_deferred_version(family_id,state);
CREATE TABLE mart_deferred_dependency (
 obligation_id VARCHAR(36) NOT NULL REFERENCES mart_deferred_version(id),
 kind VARCHAR(30) NOT NULL, scoped_key VARCHAR(240) NOT NULL,
 PRIMARY KEY(obligation_id,kind,scoped_key),
 CONSTRAINT deferred_dependency_kind CHECK (kind IN ('LOCAL_EQUIPMENT','SCOPE_PROOF','MAPPING_INPUT','RECEIPT_RECONCILIATION'))
);
CREATE INDEX deferred_dependency_lookup ON mart_deferred_dependency(kind,scoped_key,obligation_id);
CREATE TABLE mart_deferred_event (
 id VARCHAR(36) PRIMARY KEY, event_key VARCHAR(64) NOT NULL,
 obligation_id VARCHAR(36) NOT NULL REFERENCES mart_deferred_version(id) DEFERRABLE INITIALLY DEFERRED,
 revision INTEGER NOT NULL, from_state VARCHAR(32), to_state VARCHAR(32) NOT NULL,
 action VARCHAR(20) NOT NULL, reason VARCHAR(40) NOT NULL,
 evidence_run VARCHAR(36) NOT NULL, evidence_ordinal INTEGER NOT NULL,
 target_digest VARCHAR(64), at TIMESTAMPTZ NOT NULL, fence BIGINT NOT NULL, owner VARCHAR(36) NOT NULL,
 CONSTRAINT deferred_event_key UNIQUE(event_key),
 CONSTRAINT deferred_event_revision UNIQUE(obligation_id,revision),
 CONSTRAINT deferred_event_input FOREIGN KEY(evidence_run,evidence_ordinal) REFERENCES mart_capture_item(run_id,ordinal),
 CONSTRAINT deferred_event_action CHECK(action IN ('OBSERVED','ATTEMPT','SUPERSEDED','ELIGIBLE','BLOCKED','RESOLVED')),
 CONSTRAINT deferred_event_reason CHECK(reason IN ('CAPTURE_DISPOSITION','SOURCE_VERSION_CHANGED','DEPENDENCY_READY','VALID_RECEIPT','REVIEW_REQUIRED','ATTEMPT_LIMIT'))
);
ALTER TABLE mart_deferred_version ADD CONSTRAINT deferred_last_event
 FOREIGN KEY(last_event) REFERENCES mart_deferred_event(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE mart_deferred_version ADD CONSTRAINT deferred_resolution_event
 FOREIGN KEY(resolution_event) REFERENCES mart_deferred_event(id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE mart_deferred_occurrence (
 run_id VARCHAR(36) NOT NULL, ordinal INTEGER NOT NULL,
 obligation_id VARCHAR(36) NOT NULL REFERENCES mart_deferred_version(id),
 PRIMARY KEY(run_id,ordinal),
 CONSTRAINT deferred_occurrence_input FOREIGN KEY(run_id,ordinal) REFERENCES mart_capture_item(run_id,ordinal)
);
CREATE INDEX deferred_occurrence_version ON mart_deferred_occurrence(obligation_id);
CREATE FUNCTION mart_deferred_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'deferred evidence is append-only';
END $$;
CREATE TRIGGER deferred_event_immutable BEFORE UPDATE OR DELETE ON mart_deferred_event
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_dependency_immutable BEFORE UPDATE OR DELETE ON mart_deferred_dependency
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_occurrence_immutable BEFORE UPDATE OR DELETE ON mart_deferred_occurrence
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_append_only();
CREATE FUNCTION mart_deferred_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d VARCHAR(40); l mart_capture_domain; e mart_deferred_event;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'deferred debt cannot be deleted'; END IF;
 SELECT domain INTO d FROM mart_deferred_family WHERE id=NEW.family_id;
 SELECT * INTO l FROM mart_capture_domain WHERE domain=d FOR UPDATE;
 IF l.fence IS DISTINCT FROM NEW.fence OR l.owner IS DISTINCT FROM NEW.owner OR l.lease_until<=clock_timestamp() THEN
  RAISE EXCEPTION 'stale deferred writer';
 END IF;
 IF TG_OP='UPDATE' THEN
  IF ROW(NEW.id,NEW.family_id,NEW.version,NEW.fingerprint,NEW.first_run,NEW.first_manifest,
      NEW.first_ordinal,NEW.predecessor_id,NEW.scope_proof,NEW.site,NEW.organization,NEW.canonical_id,NEW.classification,NEW.reason,NEW.first_at)
    IS DISTINCT FROM ROW(OLD.id,OLD.family_id,OLD.version,OLD.fingerprint,OLD.first_run,OLD.first_manifest,
      OLD.first_ordinal,OLD.predecessor_id,OLD.scope_proof,OLD.site,OLD.organization,OLD.canonical_id,OLD.classification,OLD.reason,OLD.first_at)
    OR OLD.state IN ('RESOLVED','SUPERSEDED_BY_NEW_VERSION') OR NEW.revision<>OLD.revision+1 THEN
   RAISE EXCEPTION 'invalid deferred revision';
  END IF;
  IF NOT ((OLD.state IN ('OPEN','ELIGIBLE_FOR_RETRY','BLOCKED_NEEDS_REVIEW') AND NEW.state='SUPERSEDED_BY_NEW_VERSION')
    OR (OLD.state IN ('OPEN','ELIGIBLE_FOR_RETRY','BLOCKED_NEEDS_REVIEW') AND NEW.state IN ('OPEN','BLOCKED_NEEDS_REVIEW'))
    OR (OLD.state='OPEN' AND NEW.state='ELIGIBLE_FOR_RETRY')
    OR (OLD.state='ELIGIBLE_FOR_RETRY' AND NEW.state='RESOLVED')) THEN
   RAISE EXCEPTION 'invalid deferred state edge';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER deferred_version_guard BEFORE INSERT OR UPDATE OR DELETE ON mart_deferred_version
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_version_guard();
CREATE FUNCTION mart_deferred_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e mart_deferred_event;
BEGIN
 SELECT * INTO e FROM mart_deferred_event WHERE id=NEW.last_event;
 IF e.id IS NULL OR e.obligation_id<>NEW.id OR e.revision<>NEW.revision OR e.to_state<>NEW.state
  OR e.fence<>NEW.fence OR e.owner<>NEW.owner THEN RAISE EXCEPTION 'missing deferred transition'; END IF;
 IF NEW.state='RESOLVED' AND (NEW.resolution_event<>e.id OR e.action<>'RESOLVED') THEN
  RAISE EXCEPTION 'missing deferred resolution';
 END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER deferred_audit_guard AFTER INSERT OR UPDATE ON mart_deferred_version
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mart_deferred_audit_guard();
CREATE FUNCTION mart_deferred_family_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'deferred identity cannot be deleted'; END IF;
 IF ROW(NEW.id,NEW.domain,NEW.source_system,NEW.source_object,NEW.source_id,NEW.scope_key,NEW.policy_epoch,NEW.mapper_epoch)
   IS DISTINCT FROM ROW(OLD.id,OLD.domain,OLD.source_system,OLD.source_object,OLD.source_id,OLD.scope_key,OLD.policy_epoch,OLD.mapper_epoch) THEN
  RAISE EXCEPTION 'immutable deferred identity';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER deferred_family_guard BEFORE UPDATE OR DELETE ON mart_deferred_family
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_family_guard();
CREATE TRIGGER deferred_no_truncate BEFORE TRUNCATE ON mart_deferred_family FOR EACH STATEMENT EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_no_truncate BEFORE TRUNCATE ON mart_deferred_version FOR EACH STATEMENT EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_no_truncate BEFORE TRUNCATE ON mart_deferred_event FOR EACH STATEMENT EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_no_truncate BEFORE TRUNCATE ON mart_deferred_dependency FOR EACH STATEMENT EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER deferred_no_truncate BEFORE TRUNCATE ON mart_deferred_occurrence FOR EACH STATEMENT EXECUTE FUNCTION mart_deferred_append_only();
COMMIT;

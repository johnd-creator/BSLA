-- Disabled B3 candidate. Apply ONLY to a separately verified disposable fixture.
-- Requires reviewed 004 then 005. No source/target/debt history is rewritten.
CREATE TABLE mart_replay_queue (
 family_id varchar(64) PRIMARY KEY REFERENCES mart_deferred_family(id),
 obligation_id varchar(36) NOT NULL REFERENCES mart_deferred_version(id),
 domain varchar(40) NOT NULL REFERENCES mart_capture_domain(domain),
 scope_key varchar(40) NOT NULL CHECK(scope_key='BSR:IP:WO_BSR'),
 policy_epoch varchar(64) NOT NULL CHECK(policy_epoch='deferred-v1-BSR-IP-WO-BSR'),
 replay_epoch varchar(64) NOT NULL CHECK(replay_epoch='replay-v1-exact-id'),
 policy_digest varchar(64) NOT NULL,
 phase varchar(20) NOT NULL CHECK(phase IN ('PENDING','CLAIMED','CAPTURED','WRITING','FAILED','PROJECTED','DONE','BLOCKED')),
 reason varchar(40) NOT NULL CHECK(reason IN ('REGISTERED','CLAIMED','CAPTURED','ATTEMPT','WRITE_FAILED','PROJECTED','RESOLVED','NOT_READY','UNKNOWN','INVALID_MAPPING','SOURCE_ABSENT','PROBE_LIMIT','ATTEMPT_LIMIT','HISTORY_LIMIT','SOURCE_CHANGED','RESUMED','POLICY_MISMATCH')),
 due_at timestamptz NOT NULL, probes integer NOT NULL CHECK(probes BETWEEN 0 AND 64),
 attempts integer NOT NULL CHECK(attempts BETWEEN 0 AND 20),
 revision integer NOT NULL CHECK(revision BETWEEN 1 AND 256),
 run_id varchar(36) UNIQUE REFERENCES mart_capture_run(id), owner varchar(36) NOT NULL,
 fence bigint NOT NULL CHECK(fence>0)
);
CREATE INDEX replay_due ON mart_replay_queue(domain,scope_key,policy_epoch,replay_epoch,policy_digest,due_at,family_id)
 WHERE phase IN ('PENDING','CLAIMED','CAPTURED','WRITING','FAILED','PROJECTED');
CREATE TABLE mart_replay_event (
 id varchar(36) PRIMARY KEY, family_id varchar(64) NOT NULL REFERENCES mart_replay_queue(family_id),
 obligation_id varchar(36) NOT NULL REFERENCES mart_deferred_version(id),
 revision integer NOT NULL, phase varchar(20) NOT NULL, reason varchar(40) NOT NULL,
 probes integer NOT NULL, attempts integer NOT NULL, run_id varchar(36) REFERENCES mart_capture_run(id),
 owner varchar(36) NOT NULL, fence bigint NOT NULL, at timestamptz NOT NULL,
 UNIQUE(family_id,revision)
);
CREATE FUNCTION mart_replay_queue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d mart_capture_domain;
BEGIN
 IF TG_OP IN ('DELETE','TRUNCATE') THEN RAISE EXCEPTION 'replay evidence retained'; END IF;
 SELECT * INTO d FROM mart_capture_domain WHERE domain=NEW.domain FOR UPDATE;
 IF (d.owner,d.fence) IS DISTINCT FROM (NEW.owner,NEW.fence) OR d.lease_until IS NULL OR d.lease_until<=clock_timestamp()
 THEN RAISE EXCEPTION 'replay fence invalid'; END IF;
 IF NOT EXISTS(SELECT 1 FROM mart_deferred_family f JOIN mart_deferred_version v ON v.id=NEW.obligation_id
  WHERE f.id=NEW.family_id AND v.family_id=f.id AND f.domain=NEW.domain AND f.scope_key=NEW.scope_key
  AND f.policy_epoch=NEW.policy_epoch) THEN RAISE EXCEPTION 'replay identity invalid'; END IF;
 IF NEW.run_id IS NOT NULL AND NEW.run_id IS DISTINCT FROM d.latest_run THEN RAISE EXCEPTION 'replay run invalid'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (NEW.family_id,NEW.domain,NEW.scope_key,NEW.policy_epoch,NEW.replay_epoch,NEW.policy_digest) IS DISTINCT FROM
     (OLD.family_id,OLD.domain,OLD.scope_key,OLD.policy_epoch,OLD.replay_epoch,OLD.policy_digest)
     OR OLD.phase IN ('DONE','BLOCKED') OR NEW.revision<>OLD.revision+1
     OR NEW.probes<OLD.probes OR NEW.attempts<OLD.attempts
  THEN RAISE EXCEPTION 'replay immutable identity/history'; END IF;
  IF NOT (NEW.phase=OLD.phase OR
   (OLD.phase='PENDING' AND NEW.phase='CLAIMED') OR
   (OLD.phase='CLAIMED' AND NEW.phase IN ('CAPTURED','PENDING','BLOCKED')) OR
   (OLD.phase IN ('CAPTURED','FAILED') AND NEW.phase IN ('WRITING','BLOCKED')) OR
   (OLD.phase='WRITING' AND NEW.phase IN ('PROJECTED','FAILED','BLOCKED')) OR
   (OLD.phase='PROJECTED' AND NEW.phase='DONE'))
  THEN RAISE EXCEPTION 'replay illegal stage'; END IF;
  IF NEW.attempts<>OLD.attempts AND NOT
   (OLD.phase IN ('CAPTURED','FAILED') AND NEW.phase='WRITING' AND NEW.attempts=OLD.attempts+1)
  THEN RAISE EXCEPTION 'replay attempt reservation invalid'; END IF;
  IF NEW.probes<>OLD.probes AND NOT
   (OLD.phase='CLAIMED' AND NEW.phase IN ('PENDING','BLOCKED') AND NEW.probes=OLD.probes+1)
  THEN RAISE EXCEPTION 'replay readiness probe invalid'; END IF;
 ELSE
  IF NEW.phase<>'PENDING' OR NEW.run_id IS NOT NULL OR NEW.probes<>0 OR NEW.attempts<>0 OR NEW.revision<>1 THEN RAISE EXCEPTION 'replay initial revision'; END IF;
 END IF;
 IF NEW.phase='DONE' AND NOT EXISTS(
  SELECT 1 FROM mart_deferred_version v JOIN mart_deferred_event e ON e.id=v.resolution_event
  JOIN mart_capture_item i ON i.run_id=e.evidence_run AND i.ordinal=e.evidence_ordinal
  WHERE v.id=NEW.obligation_id AND v.state='RESOLVED' AND e.action='RESOLVED'
  AND e.evidence_run=NEW.run_id AND i.acked_at IS NOT NULL AND i.fingerprint=v.fingerprint
  AND i.disposition IN ('PROJECTED','UNCHANGED','EXPECTED_EXCLUSION'))
 THEN RAISE EXCEPTION 'replay resolution proof missing'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mart_replay_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mart_replay_event e WHERE e.family_id=NEW.family_id AND e.revision=NEW.revision
 AND (e.obligation_id,e.phase,e.reason,e.probes,e.attempts,e.run_id,e.owner,e.fence) IS NOT DISTINCT FROM
 (NEW.obligation_id,NEW.phase,NEW.reason,NEW.probes,NEW.attempts,NEW.run_id,NEW.owner,NEW.fence))
 THEN RAISE EXCEPTION 'replay audit missing'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER replay_queue_guard BEFORE INSERT OR UPDATE OR DELETE ON mart_replay_queue
 FOR EACH ROW EXECUTE FUNCTION mart_replay_queue_guard();
CREATE TRIGGER replay_queue_no_truncate BEFORE TRUNCATE ON mart_replay_queue
 EXECUTE FUNCTION mart_replay_queue_guard();
CREATE CONSTRAINT TRIGGER replay_audit_guard AFTER INSERT OR UPDATE ON mart_replay_queue
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mart_replay_audit_guard();
CREATE TRIGGER replay_event_immutable BEFORE UPDATE OR DELETE ON mart_replay_event
 FOR EACH ROW EXECUTE FUNCTION mart_deferred_append_only();
CREATE TRIGGER replay_event_no_truncate BEFORE TRUNCATE ON mart_replay_event
 EXECUTE FUNCTION mart_deferred_append_only();

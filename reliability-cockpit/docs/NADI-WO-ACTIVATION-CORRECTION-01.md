# Integrated WO activation correction

Requirement: NADI-WO-INTEGRATED-ACTIVATION-CORRECTION-01. Source qualification,
operational approval, activation, real-data browser UAT and PO acceptance remain
separate milestones. This document contains no plant exports or credentials.

The previous service cutover stopped before WO recovery DML at a strict Docker
HostConfig comparison. Its rollback used `compose start` for the two writers;
that command followed the existing `maximo-init` dependency. Init can check/create
local metadata and attempt equipment-status baseline seeding. Equal table/schema
fingerprints establish retained-state equality at the measured snapshots, not
absence of process starts, DB connections or attempted idempotent statements.
Docker's policy RestartCount does not count every manual start. Preserve last
start/finish times, lifecycle events, logs, schema/ledger and data evidence.

## Exact service operations

`deploy/development/wo_service_activation.py` defaults to read-only preflight.
It accepts only Maximo API, WO worker, Mart projector and Factual API. All other
services are outside the allowlist; init/database/migration roles are explicitly
forbidden. Each service uses its own existing project, env file and ordered
Compose overrides, all sealed by the private exact plan. Rendered images,
commands, environment, dependencies, hooks, networks and volumes are checked.
Only image/revision and the already proposed projector contract-root delta may
change. No public helper contains runtime credentials or authorizes DB writes.

- Quiesce only a writer: `stop --timeout 60 <service>`.
- Replace or restore an API: `up -d --no-deps --no-build --pull never --force-recreate <service>`.
- Replace or restore a stopped writer: same flags plus `--no-start`.
- Resume an existing exact writer: `up -d --no-deps --no-build --pull never --no-recreate <service>`.

No broad `up`, `start`, `restart`, `create`, `down`, build, pull, dependency
recreation, schema initialization or automatic migration is admitted. The private
owner GO pins the plan digest, operator and time window. Immutable image and
rollback availability, engine/context/version identity and all35role identities
are required. Durable private pre-operation/observed/completed receipts preserve
state even on an unsuccessful command. Unrelated lifecycle events or changed
identity/state/start time/restart count/config/mount/network fail the operation.
The coordinator must stop and execute the approved rollback; this helper never
silently retries a failed step or changes official paired-controller admission.

## Docker representation checks

Compare exact Env key/value maps (duplicate keys rejected), ignoring their
ordering and Docker-generated hostname/config-hash/image/config-file labels.
A generated replacement label is accepted only for the same exact service name.
Source revision labels remain exact. Normalize only present null DNS lists to
empty lists and present null OomKillDisable to false. Missing keys, actual DNS
values, OOM-disable=true, port/resource/security flags, command, user, entrypoint,
mounts, networks and other labels remain protected. This is a bounded default
comparison, not permission to waive arbitrary HostConfig differences.

## Qualification and stop boundary

`wo_service_rehearsal.py` copies only the actual dependency graph into disposable
shell fixtures. They have no source/DB credentials, DB server, host ports or
external network. It exercises the same command builder and runtime admission
through stop/replacement/resumption/rollback, captures Docker lifecycle events,
and asserts init/unrelated states remain identical. A separate armed fixture
reproduces the old `compose start` hazard. Temporary fixture cleanup checks that
the operational inventory remained untouched. This tests Docker behavior, not
application or real-data browser UAT.

Exact-head NADI CI runs the safety negatives and actual Docker rehearsal. Required
Maximo qualification and historical F01–F24/controller/security/rollback guards
remain unchanged. All CI and independent source/security/technical review must
PASS at the final head. Operator-private evidence records actual versions and
counts; source/qualified CI alone does not establish local release visibility.

Before cutover refresh identities/ledger/cursors, three DB backups and independent
restore, exact approved date/detail plans, concurrent-worker field rollback and
newer-evidence refusal. Retained source versions and Registry membership must
match for each bounded batch. The prior37,735 count confers no new data authority.
Only a separately sealed, owner-approved exact batch manifest permits writes.
No cursor reset, source query expansion, grant change or additional data cohort.
Normal polling remains independently PARTIAL/PAGE_LIMIT where observed; a polling
interruption cannot establish unseen-source completeness. Record that limit.

If command, source/image tuple, batch manifest or time window differs from the
previous approval, obtain one consolidated exact operational decision after
preparation/review. Refresh expired Engineer authentication only when the official
controller rejects it. Use that Engineer for actual Beranda → Asset → Maintenance
→ WO Detail, authorized hierarchy and PdM regressions, private screenshots and
SQL reconciliation. Never substitute ADMIN or claim dummy-fixture UAT.

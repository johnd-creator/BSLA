# Volatile CEMS service

## Source-only release

`src/live/` supplies a shared read-only service: five-second sampling, a six-hour
RAM window and once-per-minute data-signal summaries. Restart loses the window.
It does not persist samples, replace historical stores, push regulatory reports,
or infer health, operating state, downtime, MTBF or MTTR.

A public clone defaults to no NADI bridge URL. Source mode must be explicitly
selected. Simulation is visibly labelled. PLC mode requires a verified numeric
host, `--confirm-exclusive-reader`, and a fail-closed check that retained legacy
apps are stopped with restart policy `no`. The launcher also acquires one local
process ownership lock. The check is not a substitute for verifying other
source readers on the host or network.

## Safety and bounds

- One serial PLC reader, FC03/FC04 only; registry-driven addresses and existing
  normalization/operator overrides, never guessed registers or write operations.
- Five-second cycle starts, a four-second cycle budget, 500 ms transport timeout,
  50 ms request gap, no retries, overlap or catch-up queue.
- At most 32 parameters and 4,320 samples each. Six-hour expiry uses monotonic
  acquisition age, with an independent janitor. Clock regression fails closed.
- Values become stale at 15 seconds and offline at 60 seconds. Missing, invalid,
  stale and failed values remain null; a legitimate numeric zero stays zero.
- GET-only snapshot/history/signals APIs on loopback, no-store responses, bounded
  history and request concurrency. HTTP requests never initiate PLC reads.
- Minute summaries describe received samples only. They share the same cache and
  do not perform an extra source poll. They are stale after 75 seconds.
- No sample database, append log, browser persistence or raw-register logging.
  Application RAM retention is not forensic erasure or OS swap protection.

## Isolated checks and simulator

From `cems-collector/`, reuse the existing dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.live --source simulation --port 8013
```

Do not leave a simulator under an operational preview without clear labelling.
The optional NADI URL is `CEMS_LIVE_API_BASE=http://127.0.0.1:8013`.
Endpoints are `/v1/cems/snapshot`, `/v1/cems/history?parameter=SO2&limit=360`,
`/v1/cems/signals` and `/health`.

## Authorized cutover and rollback

Before PLC mode, inventory exact collector/container/service identities and their
restart policies, verify the existing history store and recovery backup, obtain
approval for the reader transition, and confirm consumers have an agreed history
path. Retained legacy persistence services are under the `cems-legacy-storage`
profile so an ordinary Compose launch cannot start them beside the RAM reader.
Do not start this profile while the volatile PLC reader is active.

For rollback, stop the volatile reader first and verify it released ownership.
Restore only the exact recorded legacy app identities and previous restart
policies. Restore only the corresponding CEMS bridge/configuration changes,
preserving unrelated later edits. Never mass-recreate the stack, run duplicate
workers, drop a volume or restore a dump over newer data as a shortcut.

The existing history DB is retained. This release has no external historical-read
adapter and does not verify history completeness or regulatory suitability.
Installation evidence, addresses, image pins and backups remain private.
See [NADI contract](../../NADI/docs/cems-live.md).

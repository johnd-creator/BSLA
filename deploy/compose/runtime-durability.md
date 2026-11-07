# Optional private runtime durability

These helpers operate a separately reviewed, local archived release. The public
repository does not contain its image IDs, lock, source snapshots, image archive,
configuration fingerprints, operational reports or credentials. A Git clone alone
cannot reproduce or restart that captured release. No service is changed by clone,
installation, tests or publication.

## Existing installation

Keep the active checkout's verified Compose files, environment, image lock and
private release package intact. Do not replace local image pins with `build:` to
silence a missing-image error, and do not run broad Compose startup or remove
orphans to restart one service. Retained rollback containers may share labels.
Never start a backup source worker alongside an active worker. Preserve project,
network, stores, volumes, least-privilege reader DSN and worker commands.

The controller accepts only five known application services and checks an exact
name, immutable image, project, network and duplicate workers. Recreate compares
replacement configuration before stopping the original, retains the original for
rollback and resolves uncertain creation before attempting recovery. Environment
values are compared in memory, not written in operation reports. The code does
not approve a deployment or make a local archive portable.

## Private inputs

- `BSLA_RUNTIME_LOCK`: absolute path of the reviewed JSON lock. The default is an
  ignored `runtime-images.lock.json` inside the repository's `.nadi-dev` directory.
  The example schema deliberately contains invalid placeholder IDs and cannot
  authorize an operation. Provision real local IDs separately after review.
- `BSLA_RUNTIME_RELEASE_DIR`: private release directory containing captured source,
  archive and verification evidence. Default: the ignored `.nadi-dev/runtime-release`.
  Existing installations should select their existing directory without copying,
  rewriting or recapturing it. Preserve private capture files and fingerprints.
- `BSLA_RUNTIME_COMPOSE_FILES`: JSON list of reviewed Compose paths, in overlay
  order. The defaults are root `compose.yaml` and `compose.dev.yaml`; they are
  buildable installation definitions and intentionally fail locked-runtime
  validation. Supply the existing private pinned model or approved local overlay
  that removes build definitions, sets immutable IDs and `pull_policy: never`.
  Do not change project, worker commands, environments or volume identities.

An absent lock or release fails before any Docker service action. No guessed image,
registry pull, automatic capture or build fallback is attempted. Keep private files
ignored. Never commit resolved Compose environment output or archived runtime data.

## Deliberate operations

Only after reviewing those private inputs and authorizing the relevant operation:

- `runtime_release.py verify` checks running identities, desired image selection,
  environment and commands. It is read-only and withholds environment values.
- `runtime_service.py restart SERVICE` restarts one exact service.
- `runtime_service.py recreate SERVICE` preserves the original stopped container.
  Its recorded private operation file supports `runtime_service.py rollback FILE`.
- `runtime_release.py capture` creates a new private archive without overwriting
  an existing capture. Review image/source content before using or sharing it.
- `runtime_release.py rebuild` replays captured source over exact locally archived
  dependencies with networking disabled. It does not activate candidate images.
- `rehearse_runtime.py` is opt-in: isolated no-network containers exercise the
  local images and synthetic tests, then compare original container identities.
  It requires the private capture and rebuilt images and does not run on fresh CI.

Restoring an archive and replaying captured source are distinct: replay can produce
a new image ID and does not establish reproducibility from this Git tree. A fresh
installation must deliberately follow the platform runbook, provision appropriate
configuration and validate its own build; it must not inherit another installation's
image identity, freshness policy or claimed runtime verification.

## Public verification

`python3 -m unittest discover -s deploy/compose/tests` tests synthetic locks,
missing inputs, immutable image selection, exact configuration cloning, failed
activation, rollback, duplicate workers and concurrent deployment. It performs
no Docker operation and uses no private lock or source data. Projector regressions
under `release_tests` exercise synthetic stored Collector rows. Actual local image
restart/recreate/archive evidence remains private and is not claimed by CI.

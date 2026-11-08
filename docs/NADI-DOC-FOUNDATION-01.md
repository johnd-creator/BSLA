# NADI-DOC-FOUNDATION-01 — documentation audit and governance

## FIX-03 current merge reconciliation — 2026-10-10

Verified main `0cb26882c870185a54282df3af4a136f31702b67`; PR62 merged via
`72b7ec55acbb3d5d9562102c3eaf721d4dda714b`, PR63 merged via latest main above.
PR64 previous HEAD `403cad8cea1a4d1606484e71136f8843abd4ab96` was clean before merge.
Actual conflicts: `plans/NADI-ROADMAP.md`, `plans/REPOSITORY-STATUS.md` and
`plans/reliability-cockpit-platform/05-roadmap-implementasi.md`.

Resolution combines product phases/UX track with PdM requirements and developer
runbooks. One current product phase table remains authoritative; the dated PR63
checkpoint stays in the roadmap, while repository status links to its owning packet
instead of repeating its backlog. The technical roadmap retains PR62's historical
startup/acceptance checkpoint beneath the updated merge status. Historic test and
acceptance text is preserved; stale OPEN statements below are dated observations.

PR62 launcher/source code/runtime config and all PR63 packet/manual-PdM/Phase3
files are byte-identical to latest main. Product requirements, Design System,
11 UI specs, five PNG references/provenance and documentation governance remain.
No original image, XLS, runtime, collector or database is modified. New PR64 HEAD
and CI evidence are in its handoff. PR64 is not automatically merged.

Current local authorities: [single-frontend runbook](../reliability-cockpit/docs/nadi-dev-reset-01.md)
and [PdM requirements/gates](../reliability-cockpit/docs/nadi-pdm-requirements-01.md).
The pinned links and reconciliation plan below retain historical provenance; their
unmerged status wording does not override this checkpoint.

## Historical FIX-02 and foundation checkpoints

## FIX-02 superseding reference checkpoint — 2026-10-10

The Product Owner confirms the existing root PNGs as official references:
konsep1 Action Board, konsep2 Recommendations, konsep3 PdM Center, konsep4 Asset
Health Detail, konsep5 Executive Overview. All five were visually inspected and
matched to tracked main bytes; the [manifest](design/references/README.md) records
format, size and unchanged SHA256. No ZIP/JPG or duplication is required.
This resolves the image-availability limitation and D03 provenance gap recorded
below. Earlier MISSING statements describe the initial foundation audit only;
its acceptance evidence remains preserved. UI implementation acceptance, token/
contrast review and engineer-validation gates are still separate.

PR64 remains OPEN on codex/nadi-doc-foundation-01; PR62/63 were rechecked OPEN at
the same exact heads shown below. Main remains f54643f3510bf505628a1400024784faab46e496.
This follow-up changes documentation only; no source, runtime or database action.

## Historical foundation audit (before FIX-02)

Audit date: 2026-10-10, Asia/Jakarta. Scope: documentation only.
Branch: `codex/nadi-doc-foundation-01`, separate clean worktree from verified main.
No active checkout switch, runtime restart, source request, DB write or policy change.

## Verified repository and runtime baseline

| Artifact | Exact revision | State at audit |
|---|---|---|
| `origin/main` | `f54643f3510bf505628a1400024784faab46e496` | Latest fetched main; includes merged PR61 |
| PR #62, `codex/nadi-dev-live-01` | `0bfea1273f97ce96a08ef147b44f804aecb428d1` | OPEN; active clean 3000 preview |
| PR #63, `codex/nadi-pdm-req-01` | `89cfa0e50dbdaa1fa158558c890cc512c049b60f` | OPEN; clean separate documentation worktree |
| Original workspace, `feature/pi-governed-source-adapter` | `0c800dac1da6ef863afdb193021176fe7feac073` | Preserved; original untracked `23496711.xls` |

GitHub queries verified [PR62](https://github.com/johnd-creator/reliability-knowledge-starter/pull/62)
and [PR63](https://github.com/johnd-creator/reliability-knowledge-starter/pull/63) independently;
neither was merged by this task. Merged PR29–61 supply Engineering, inspections,
recommendations, identity, persistence, HTTP QA and local-login foundations. Older
OPEN/candidate statements in their reports are historical checkpoints, not current
merge status. Merge does not imply operational activation.

Backend/frontend CI succeeded for [main/PR61](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/37921470470),
[PR62](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/37940329956)
and [PR63](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/37932325576).
These runs do not certify this new documentation commit or runtime visibility.

Read-only runtime inventory: `nadi-primary-web.service` owns HTTPS port3000,
MainPID262322; `nadi-live-api.service` owns isolated Engineering API, MainPID163367.
`nadi-live-web.service` is inactive (MainPID0), legacy13035 retired. Existing fixture
identity is `nadi_live_dev_test`, explicitly SYNTHETIC_FIXTURES/DISPOSABLE_TEST.
The status endpoint reports frontend/launched/backend SHA equal to PR62 head,
dirty=false, stale=false, factual and Engineering backends AVAILABLE. Availability
is not evidence freshness. No browser login or new QA mutation was performed here.
The docs branch is not loaded by the active frontend.

The original XLS SHA256 is
`aa0bd8fd22275aea3ecf8654ee37878106123b7dbdf58135fb783e853ee66a5f`.
Private before/after inventories retain exact container IDs/start times; public
summaries omit operational addresses, secrets, cookies and private configuration.
Existing worker activity was observed only; this task neither authorizes nor retries
PI/Maximo/CEMS acquisition. Historical source handoffs must be rechecked by an
independently authorized operational task.

## Authority map

| Document | Owns | Does not certify |
|---|---|---|
| [AGENTS](../AGENTS.md) + scoped instructions | Safety and execution conventions | Product completion |
| [NADI Context](../NADI-CONTEXT.md) | Short onboarding and authoritative links | A duplicate roadmap |
| [PRD](../PRD.md) | Product requirements, IDs, acceptance and dependencies | Runtime implementation or engineer approval |
| [Design System](../DESIGN-SYSTEM.md) | Proposed visual/component rules | Engineering severity or final visual acceptance |
| [UI specification](design/NADI-UI-SPEC.md) | Page layout/interaction requirements | Existing functionality without evidence |
| [Current plans](../plans/README.md) | Active Laravel and MTBF/MTTR work; links to historical phase references | Automatic deployment authority |
| [Repository Status](../plans/REPOSITORY-STATUS.md) | Git/runtime checkpoints and debt | Fresh source facts from old reports |
| [DEV-LOG](../DEV-LOG.md) | Append-only milestone events | Approval inferred from tests |
| [Technical M0–M8](https://github.com/johnd-creator/BSLA/blob/cea9503c9c605d8a060d448e36a16cf1ea646089/plans/reliability-cockpit-platform/05-roadmap-implementasi.md) | Historical engineering delivery dependencies | Current backlog or a competing product roadmap |
| Scoped ADRs, contracts, semantic/acceptance docs | Their architecture, data and evidence scopes | Broadening approved semantics through design |

Reviewed GitHub documents are the durable project knowledge source. Link exact PRs
or immutable commits for pending work. A local candidate remains a proposal until
reviewed; a merge remains distinct from deployment and PO acceptance. Preserve
historical reports. When a statement changes, add a dated superseding checkpoint
with evidence rather than rewriting the original observation.

## Decision and proposal register

| ID | Direction / provenance | Disposition |
|---|---|---|
| D01 | NADI product identity and PLTU Banten 1 Suralaya context; supplied DOC-FOUNDATION task | Product Owner direction recorded; no claim of implemented rebranding |
| D02 | One primary HTTPS3000 address; DEV-RESET request and PR62 acceptance | Development direction; acceptance PASS within developer-tested scope; merge separate |
| D03 | Asset Detail six sections and supplied screenshot declared visual target; DOC-FOUNDATION task | PO layout direction; original image inaccessible, visual comparison pending |
| D04 | Global login design first, no global enforcement now; DOC-FOUNDATION task | Binding task boundary; current QA security preserved |
| P01 | Palette, component dimensions and responsive behavior | PROPOSED; contrast/accessibility and PO review pending |
| P02 | Eight top-level navigation entries and technical relocation | PROPOSED; preserve routes; Engineering access placement needs review |
| P03 | PR63 R01–R08/Q01–Q10/M01–M07 | Candidate requirements; engineer validation pending, not field/threshold approval |

For later decisions record ID, requirement/task, decision maker, date/time or DATE_ONLY,
exact scope, rationale, evidence, affected documents, expiry if applicable and
superseded decision. Distinguish direct PO instructions, repository-reported approval,
executor proposal and UNKNOWN. An executor cannot sign off for actual engineers.
This register is a record of supplied direction, not manufactured signed acceptance.

## PR62 / PR63 reconciliation plan

PR62 owns the existing single-frontend launcher and development runbooks. Its
[pinned reset runbook](https://github.com/johnd-creator/reliability-knowledge-starter/blob/0bfea1273f97ce96a08ef147b44f804aecb428d1/reliability-cockpit/docs/nadi-dev-reset-01.md)
is the startup/source-selection/rollback authority while unmerged; the earlier
[live-development report](https://github.com/johnd-creator/reliability-knowledge-starter/blob/0bfea1273f97ce96a08ef147b44f804aecb428d1/reliability-cockpit/docs/nadi-dev-live-01.md)
retains historical13035 evidence. Do not run its superseded startup instructions.
No copied launcher or alternative implementation is introduced.

PR63 owns the [pending PdM requirements packet](https://github.com/johnd-creator/reliability-knowledge-starter/blob/89cfa0e50dbdaa1fa158558c890cc512c049b60f/reliability-cockpit/docs/nadi-pdm-requirements-01.md),
manual-PdM clarification and Phase3 diagnostic addendum. This foundation references
its exact R/Q/M IDs without approving method fields, cadence, scores or PD=DGA.

Likely textual conflicts: PR63 prepends to `plans/NADI-ROADMAP.md` and
`plans/REPOSITORY-STATUS.md`; PR62 prepends to technical M0–M8. This branch adds dated
foundation notes to the same entrypoints. Neither candidate document is overwritten.

1. Review each PR at its exact head. No merge order is authorized by this report.
2. When an authorized merge occurs, fetch latest main in a separate clean worktree;
   reconcile this documentation branch against it, never the running preview checkout.
3. Keep both dated checkpoints and all PR63 R01–R08, Q01–Q10 and M01–M07 content;
   keep PR62 runbooks/acceptance. Resolve overlapping headers explicitly, not with
   wholesale ours/theirs selection. Current phase/merge states must agree with GitHub.
4. Convert pinned candidate links to local links only after files exist on merged main;
   retain immutable links as historical evidence. Keep one official product roadmap.
5. Recheck relative links, historical preservation, milestone wording and exact-head
   checks. Runtime cutover, PdM implementation and global enforcement remain separate.

## Phase1 governance continuity

[Phase1 acceptance](../plans/NADI-PHASE-1-ACCEPTANCE.md) and
[GOV03](../reliability-cockpit/docs/nadi-p1-fresh-gov-03.md) retain authority.
Activation recorded 2026-10-08T21:45:26.619585+07:00; independent reviews due
2026-10-09T21:45:26.619585+07:00 (24h) and
2026-10-11T21:45:26.619585+07:00 (72h); owner checkpoint
2026-10-12T20:00:00+07:00; hard expiry **2026-10-13T00:00:00+07:00**.
Operator review outcomes are UNKNOWN in the evidence available to this audit.
The 24h deadline has elapsed as of this audit date; do not infer review completion.
No automatic scheduler exists. The original date-only approval, exact revised expiry,
condition-policy unknowns and accountable operator remain unchanged. No extension,
activation, reset or rollback is performed or authorized by this documentation task.

## Audit method and limitations

Read root entrypoints, current/historical roadmap checkpoints, Phase1 acceptance,
platform M0–M8 proposal headers, scoped instructions, ADR006/007, factual release
semantics, authentication/Engineering reports, contracts catalog, current frontend
navigation/gates/configuration and PR62/63 diffs/runbooks. This is a task-directed
documentation audit, not an exhaustive source/security review or new data audit.
Codebase Memory Tier2: AppShell lookup, both-direction trace to RootLayout, snippet
and coverage. Graph generation2026-08-24 predates main and indexes the original
checkout; stale/missing scopes were checked from the new worktree's exact source.
No graph completeness claim is made. Cockpit has no CONTEXT.md at this baseline;
root context plus scoped AGENTS and technical docs provide onboarding.

Three actual reference JPGs are unavailable; [manifest](design/references/README.md)
records missing originals. Historical concept PNGs were not substituted. The task
message ends mid-section12 after onboarding item2; clarification was requested.
The added sequence implements the complete visible requirements without asserting
that an unseen continuation was received.

Documentation checks and final milestone evidence are appended to [DEV-LOG](../DEV-LOG.md).
Application/collector/DB tests need not be rerun for Markdown-only changes. CI
workflow path filters may not schedule jobs for root/plans/design-only edits;
report NOT RUN if so, never infer a new CI PASS from older runs.


## Documentation validation — 2026-10-10

PASS: 14 Markdown files only; 11 page specifications contain all required sections;
99 added relative references resolve (before final log links); existing AGENTS bytes
remain an unchanged prefix, and original roadmap/status/M0–M8 historical content is
retained. `git diff --check` passes. No JPG was fabricated or substituted.

Read-only preservation check: all18 NADI/fixture containers in the baseline retain
exact IDs/start times; development unit states/PIDs and full sanitized development
status match; active and PdM worktrees remain clean at their original SHAs. Original
workspace still has only untracked `23496711.xls`, with identical SHA256. The wider
Docker inventory also contains unrelated pre-existing services outside this audit's
baseline; no whole-host inventory equality is claimed. No database content query,
login mutation, HMR edit, restart or operational browser workflow was run for docs.

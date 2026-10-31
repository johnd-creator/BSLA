# Sprint 1 visual and interaction evidence

All images use **actual imported React components** and identical labeled synthetic
fixtures. All requests are intercepted on `.invalid`; no live application/plant data,
TLS bypass, active session, source request or runtime activation is involved.

Before: immutable blueprint `2437fdb3b12f8ab63d56236dbb532caa7e39b671` from git archive.
After: the candidate implementation containing this evidence. The delivery PR binds
the exact final SHA and terminal backend/frontend CI. The common fixture/setup hash
and all 112 image hashes are in [manifest.json](manifest.json).

| Screen (1440 light preview) | Before | After |
| --- | --- | --- |
| navigation | [Before](before/navigation-light-1440.png) | [After](after/navigation-light-1440.png) |
| pdm-register | [Before](before/pdm-register-light-1440.png) | [After](after/pdm-register-light-1440.png) |
| measurement-editor | [Before](before/measurement-editor-light-1440.png) | [After](after/measurement-editor-light-1440.png) |
| inspection-detail | [Before](before/inspection-detail-light-1440.png) | [After](after/inspection-detail-light-1440.png) |
| native-history | [Before](before/native-history-light-1440.png) | [After](after/native-history-light-1440.png) |
| excel-history | [Before](before/excel-history-light-1440.png) | [After](after/excel-history-light-1440.png) |
| case-handoff | [Before](before/case-handoff-light-1440.png) | [After](after/case-handoff-light-1440.png) |

Every scene also has matching `*-{light,dark}-{390,768,1440,1920}.png` files in
[before/](before/) and [after/](after/): 56 before +56 after. No static mockups.
The fixture has three authorized inspections but one row per register page,
two native events and a separate provisional source group with zero/null values.
Those synthetic populations are not operational counts or equipment assessments.

[Candidate results](after/results.json):78 checks,56 contained-page-overflow checks,
56 axe WCAG A/AA scans,0 violations,0 browser exceptions. The action hierarchy,
full four-section editor, narrow dark detail, drawer, native/Excel history and
optional Case form were also visually reviewed. Long tables retain their existing
contained keyboard scrolling; this is not complete accessibility certification.
PO usability/visual acceptance remains pending.

Additional evidence: [contract/lint groups](contract-checks.json),
[13 session/draft scenarios](auth-session-results.json),
[4 actual UI/API/PostgreSQL scenarios](ui-api-results.json),
[source-history regression](source-history-results.json), and
[full input/keyboard/review/Case retry regression](input-workflow-results.json),
[42 timezone/source-precision checks](pdm-date-results.json), and
[56 existing login/logout visual checks](login-visual-results.json). Existing source suites
and the expanded input/review/Case retry test run in exact-head candidate CI.

Reproduce from `reliability-cockpit/web` using the existing CI-pinned browser tooling:
`NADI_PLAYWRIGHT_MODULE` points to playwright1.62.1/index.mjs and `NADI_AXE_MODULE`
to @axe-core/playwright4.11.0/dist/index.mjs; run
`node scripts/pdm-simplification-browser.mjs`. Baseline uses the same runner/fixtures
in a git archive of2437fdb, with `NADI_SIMPLIFICATION_BASELINE=1`; this skips candidate
assertions/axe only. `NADI_BROWSER_OUTPUT` selects a disposable output directory.
The committed check commands/workflow supply production build, TypeScript, backend,
full input keyboard/capture/auth/Case, integration and other acceptance gates.

[Scope and F01–F24 report](../../NADI-PDM-SIMPLIFICATION-SPRINT-01.md).

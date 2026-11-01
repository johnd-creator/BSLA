# Sprint5 — consolidated PO and engineer UAT checklist

Status: HUMAN_UAT_PENDING. Owner request of 1 November2026 authorizes isolated
stabilization/testing and a stacked Draft PR; it grants no semantic approval,
merge, local activation or deployment. No UAT row below has been signed.
Exact candidate is the immutable final HEAD in the Sprint5 PR qualification receipt.
Use one consistent candidate; a changed head invalidates affected evidence.

## Review roles and evidence recording

Product Owner owns functional/visual acceptance; PdM author and independent
reviewer own record workflow UAT; reliability/maintenance/operations/historian
and contract owners sign their separate methods and source policies. Names,
review dates, signatures and observed outcomes remain UNASSIGNED/PENDING until
accountable humans record them. An ADMIN is not an independent reviewer override.
For each row record candidate SHA, tester/role, permitted asset, actual outcome,
private evidence reference and PASS/FAIL/BLOCKED with reason. Never record secrets.

| ID / accountable role | Real engineer scenario / expected outcome | Status |
| --- | --- | --- |
| U01 PO + engineer | Beranda with authorized capability;403 accurately means access denied,401 expires session; no invented healthy state | PENDING |
| U02 engineer/source owner | Asset Register→exact Asset Detail; preserve asset/site/org and prior filter on return | PENDING |
| U03 PdM author | PdM Register1/5/10: correct authorized totals, last page, filters and no hidden records | PENDING |
| U04 PdM author | Input Pengukuran: select work origin/asset, preserve typed0/null/false/text, original unit/time/provenance; missing time stays missing | PENDING |
| U05 PdM author | Cancel dirty navigation and remain with draft; deliberate discard clears it; same-session recovery preserves draft after recoverable error | PENDING |
| U06 author/reviewer | Save/update with exact revision; stale revision conflicts preserve draft; lost ACK retries same intent once, no duplicate/audit loss | PENDING |
| U07 independent reviewer | Author/inspector/contributor cannot review own record; return with reason, revise/resubmit and explicitly approve exact new revision | PENDING |
| U08 engineer | Detail→asset/method history→sample inspection→PI/Maximo evidence→return to identical history filters/page; zero/null/raw source clocks unchanged | PENDING |
| U09 engineer + M02 owner | Same-inspection sample plot only when qualified; cross-inspection trending remains NOT_ELIGIBLE; no interpolation or method/comparability sign-off inferred | PENDING |
| U10 source owner | Provisional Excel is separate from native history; raw fields/formulas/unknown clocks/profile/alias stay visible and unpromoted | PENDING |
| U11 author/reviewer | Approved native record may deliberately create Case with frozen exact reviewed revision; unapproved/provisional handoff denied; routine inspection needs no Case | PENDING |
| U12 author/reviewer | Case→Recommendation→review→reported SR/existing WO context; no Maximo write, automatic diagnosis or work authorization | PENDING |
| U13 Maximo owner | Exactasset maintenance register25/page, PM/CM/status/date filters, duplicates/conflicts and raw source detail; activity dates are not failure/restoration or sync time | PENDING |
| U14 PI/historian owner | Approved mapped latest signals only; original0/false/null/digital/type/unit/quality and source/collection/projection clocks; latest-only/history-not-qualified explicit | PENDING |
| U15 source + registry owners | VERIFIED/CANDIDATE/UNRESOLVED/FORBIDDEN and ambiguous/duplicate identities remain distinct; no alias/name/workbook join or new mapping approval | PENDING |
| U16 reliability/maintenance/operations | Laporan→Kinerja Reliabilitas: exactasset/explicit period, missing prerequisites and source drilldown; MTBF/MTTR values unavailable | PENDING |
| U17 security owner | Expired/revoked session, role/scope removal and forced logout clear private data/draft; foreign asset and reviewer exclusions enforced server-side | PENDING |
| U18 PO/accessibility reviewer |390/768/1440 mobile/tablet/desktop; light/dark changes, keyboard/focus/return, overflow, readable empty/error/loading/403 states | PENDING |
| U19 engineer + security | Advisory/Inbox/ACK, attachment custody metadata and audit history remain accessible only through existing permissions | PENDING |
| U20 PO | One coherent five-entry product flow: Beranda, Aset, PdM Center, Tindak Lanjut, Laporan; record preferences separately from blocking defects | PENDING |

## Independent gates — no automatic promotion

| Gate | Current authorization / required decision |
| --- | --- |
| Automated technical qualification | Exact final HEAD backend/frontend CI and bounded independent review; receipt on one Draft PR |
| Engineer method/source approval | PENDING: all Sprint4 decision rows remain unsigned; inspect original source evidence separately |
| PO functional/visual acceptance | PENDING: use this checklist and private synthetic package first; screenshots/axe/CI do not sign UAT |
| Operational data eligibility | NOT_ELIGIBLE: no qualified failure/exposure/repair read model or approved contracts adopted |
| Merge readiness | Recommendation conditional on dependency order114→115→116→117→Sprint5, current exact-head CI/review and owner-approved merge; no merge authorized here |
| Local activation | NOT_AUTHORIZED_IN_SPRINT5; explicit future owner authorization for one exact SHA and all gates below |
| QA/production deployment | NOT_AUTHORIZED; requires independent environment, source/data/security and release decisions |

## Required future authenticated local cutover — outside this sprint

1. Owner explicitly approves exact integrated candidate and rollback target. Recheck
   current main/dependency heads, complete CI/review, active dirty source and unmerged
   work; do not silently rebase, discard or substitute a parent candidate.
2. Use legitimate engineer/owner-assisted login and the documented official private
   controller session-proof mechanism. Verify proof without printing values. If
   unavailable, state exact owner action; no browser-cookie extraction, credential
   scraping, fabricated proof or security-gate bypass.
3. Verify immutable official controller/source digest, source seal including dirty
   overrides, frontend/backend identities and single service ownership; inspect
   worker/store boundaries without starting another source worker or frontend.
4. Verify application DB identity, migration ledger and retained business/history/
   audit/source/account/grant/session baselines. Obtain a fresh private backup via
   the approved controller; validate checksum/TOC/full decode without exposing data.
5. Independently restore only into a fresh disposable copy and compare documented
   table/ledger/record aggregates; confirm reviewed recovery source/dependencies read
   current schema and newer records. Protect sessions/grants and unrelated services.
6. Verify aa065af9 checkpoint remains compatible/recoverable and record actual
   immediate Sprint2 pair3a01e842 rollback source. Older checkpoints are not assumed
   schema-compatible. Prepare exact recovery/compatibility receipts and rollback
   evidence; a backup file alone is insufficient.
7. Revalidate session proof, source/store ownership and backup/recovery freshness
   immediately before one serialized controlled paired transition. Any gate FAIL
   means STOP and preserve current active pair. No frontend-only or backend-only
   partial activation; use official failure recovery/rollback procedure.
8. After separately authorized activation, confirm actual front/back SHAs, TLS,
   authenticated roles/scopes/CSRF, original records/audit/source counts, controller
   status and recovery readiness. Execute scoped UAT and keep factual screenshots
   owner-private. Report actual visibility separately from PO/engineer decisions.

No cutover/backup/restore/account action above was performed by Sprint5. These are
future gates, not proof they pass now. Do not merge, activate, deploy or begin a
following sprint automatically.

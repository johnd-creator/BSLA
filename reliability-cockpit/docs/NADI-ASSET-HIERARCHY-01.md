# NADI-ASSET-HIERARCHY-01 — retained Maximo hierarchy

2026-11-02 · implementation candidate; deployment and Product Owner acceptance pending.

The Asset Detail overview adds an optional, lazy-loaded hierarchy panel. It reads
existing Maximo parent relationships from the existing SELECT-only Mart. Excel is
not imported or used to infer hierarchy. Normal Asset Register membership remains
the governed Registry; technical parent/component rows are explicitly context.

| Requirement | Candidate behavior | Evidence / limit |
|---|---|---|
| H01 source identity | Exact canonical Maximo BSR/IP references and retained parent edges | Existing Collector `_asset_record` projects the direct Maximo `parent` field; no fuzzy ID, name, or code-prefix matching |
| H02 bounded traversal | Registered root checked before count/page; requested node must prove a retained upward path to that root | Maximum 32 edges, children pages 1–50, offset 0–10000; no full-tree fan-out |
| H03 uncertainty | Missing parent, outside-scope parent, cycle and depth limit are distinct | Entire view always PARTIAL; no children retained never means verified source leaf |
| H04 source semantics | Raw type/status and exact boolean child flag remain separate from retained child count | System/equipment/component roles remain UNKNOWN; `mainstr` is not a hierarchy role |
| H05 authority | Existing fixed portfolio capability required by the browser gateway | Exact Engineering asset grants and temporary registered Factual READ do not acquire technical descendants/ancestors; denied users receive an explicit 403 state |
| H06 preservation | No new schema, store, collector, mapping, Registry membership or grant | Existing source/controller/session and historical F01–F24 pins retained; finite exact hierarchy additions only |

`GET /v1/reliability/assets/{registered_root}/hierarchy` accepts only `node_ref`,
`offset` and `limit` through its gateway rule. The backend returns a safe scalar
projection, path within the root, retained root ancestors and direct children.
Off-root, foreign-scope, unregistered-root, cyclic or over-depth descendant
requests release no child totals. Parent ancestors are context rather than new
Registry entries. A long description is an explicitly marked 1000-character
preview. No raw vendor payload, source URL, personal WO field or source credential
is returned. Source update clocks are not collection freshness or equipment health.

The existing local audit found retained technical assets and governed Registry
membership to be distinct populations, with unresolved parents and missing
retained children. Exact operational aggregates and source evidence are private;
no plant export or screenshot belongs in this repository. Stored asset type does
not currently establish the requested system/equipment/component role semantics.

Knowledge authority: `maximo-knowledge/discovery/objects/mxapiasset.json` records
the verified hierarchy fields. The owning Collector rules still restrict source
execution, fixed BSR/IP and the configured validated equipment unit. This feature
does not contact Maximo, broaden acquisition scope, import a Registry snapshot,
project new rows or recollect history. Resolving retained gaps requires a separate
bounded, source-owner-reviewed acquisition plan and verified field semantics.

Validation at the candidate source:

- 12 hermetic SQLite/API tests cover Registry admission, off-root denial before
  counts, scope/page limits, raw booleans, long previews, cycles/depth and no data
  mutation. They use disposable files, not an operational store.
- Gateway checks cover fixed portfolio identity, narrow/unrelated ADMIN denial,
  Registry lookup before hierarchy read, query isolation and post-fetch revocation.
- A network-intercepted real component harness verifies lazy loading, keyboard
  drill/back, 390/768/1440px overflow and zero axe violations, plus missing-data,
  denied and unavailable states. Screenshots are synthetic and private.
- Existing Asset/WO/Engineering behavior is retained behind the original scope
  fences. The new manifest admits a closed set of exact source hashes; original
  PR120 READ hash manifest and PR119/WO-detail historical pins remain unchanged.

Hosted exact-head CI, independent final review, merge state and actual local UAT
must be reported independently. The active PR119 runtime does not serve this new
contract. This document gives no activation, source execution or grant authority.
Logbook PdM remains HOLD. Engineer technical-hierarchy access and semantic roles
remain owner decisions; the implementation does not silently expand either.

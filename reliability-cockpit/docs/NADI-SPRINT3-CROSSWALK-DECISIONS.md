# Sprint3 read-only crosswalk decision register

No candidate is approved or persisted by this document or the offline inventory.
The runtime UI uses only authorized exact-asset condition evidence. Full mapping
candidate enumeration is blocked by the current gateway contract, deliberately
unchanged. The offline decision schema is not a new application/source endpoint.

| Existing evidence / exact scope | Recorded state | Missing decision / owner | Eligibility |
| --- | --- | --- | --- |
| `asset:MAXIMO:MXASSET:BSR:IP:CS10HFB01AF001-001`; Maximo equipment `CS10HFB01AF001-001`, BSR/IP/CS01, Coal Feeder A | VERIFIED, existing human MATCH recorded by Fauzi; one Coal Flow A signal approved separately | No new identity or signal approval; exact AF/signal refs are displayed only when present in permitted DTO, not inferred from labels | Only this recorded pilot; freshness independently qualified by existing policy |
| PI_AF_KKS_LOOKUP_UNRESOLVED | UNRESOLVED | PI/source owner must resolve exact source identifier evidence | Excluded from unsupported conclusions |
| Pulverizer A/G relationships in pilot investigation | UNRESOLVED | Responsible owner MATCH with exact canonical/source refs and dated evidence | No automatic name/alias join |
| BFPT contradictory relationship | FORBIDDEN / REJECTED / FROZEN / DO NOT VERIFY | Source owner resolution under separate governed task | Excluded; no discovery/verification here |
| Other registered assets and technical PI attributes | UNKNOWN; not a candidate approval | Exact identity, scoped evidence/method, accountable owner/date, duplicate/conflict review | No automatic promotion |
| Local DCS Historian | DISCOVERY_ONLY | Interface/owner/contract/read permissions and identity evidence not established | BLOCKED |

Authority: [accepted pilot](nadi-idn-002b-coal-feeder-a.md),
[Phase1 acceptance](../../plans/NADI-PHASE-1-ACCEPTANCE.md).
These are repository checkpoints, not a fresh query of operational mapping counts.
The earlier zero-mapping checkpoint remains historical.

Decision packet fields: canonical asset, site/org, exact Maximo equipment, actual
PI AF/signal refs if available, mapping evidence/owner/date, recorded status,
missing/duplicate/conflicting/forbidden conditions. Selection-approval provenance
cannot fill missing mapping-verification evidence. Unavailable values remain null.

`asset-crosswalk-decision.schema.json` is an additive offline review-input contract.
`catalog/evidence_readiness.py` retains every row, fails over10000 rows, preserves
FORBIDDEN, marks duplicate canonical/site/org relationships UNRESOLVED and never
promotes CANDIDATE. Multiple selected signals for one mapping must first be grouped
by their recorded mapping identity by the source owner; this inventory deliberately
requires one relationship per row. Synthetic examples are explicitly labelled and
cannot serve as actual plant mapping evidence. No persistence or source calls.

The proposal schema, examples and pure offline tool are located in
`reliability-cockpit/contracts/sprint3/`, independently tested by NADI CI. Existing
canonical shared contracts remain byte-identical; no collector consumes these
proposal files. Their future foundation adoption is a separate approval.

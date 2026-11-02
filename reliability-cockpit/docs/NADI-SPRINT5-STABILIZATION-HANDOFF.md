# Sprint5 stabilization handoff — not started

Sprint4 is an isolated technical foundation, operational KPI NOT_ELIGIBLE.
This document is a proposed handoff, not authorization to begin Sprint5, activate
Sprint4, approve methods, merge dependencies or alter source/retained services.

## Required inputs before scheduling

- Exact final Sprint4 commit, Draft PR and CI/review receipts in
  [Sprint4 delivery](NADI-PDM-SPRINT-04-DELIVERY.md). Preserve PR114→115→116 ancestry.
- Consolidated PO UI/UX review of bounded Asset/PdM/Reports workflow; no automatic
  acceptance from a screenshot or a technical PASS.
- Named reliability, maintenance, operations/historian and contract reviewers.
  Sign and version the functional failure definition, equipment membership/window,
  exposure provenance/quality/coverage, active repair versus outage, exclusion,
  overlap/reopen/censor/duplicate/supersession and historical correction policies.
- A qualified, authorized reference dataset and independently hand-reconciled
  outcomes with complete source/revision evidence. Synthetic packet sign-off is
  not a substitute for actual equipment/source evidence.

## Bounded proposed stabilization work (requires separate task)

1. Resolve method/semantic decision register in Sprint4 delivery. Compare real
   source capability against candidate fields, preserving missing/unapproved states.
2. Review any future shared-contract adoption and owning-store read model separately;
   no new DB, collector, schema activation or exposure acquisition is implied.
3. Reconcile exceptions the candidate currently rejects: cross-window/censored or
   reopened repairs, repeated restorations, interval/episode overlaps and outage
   contradictions. Change policies only after scoped engineering approval.
4. Repeat exact-head source/contract/auth regression and negative/large-fixture UI
   qualification. Evaluate actual DB plans only under separately authorized local
   read-only scope; synthetic timings are not an operational SLA.
5. PO visual acceptance and engineer source/method acceptance stay separate. Any
   future local promotion needs explicit owner action, official session proof,
   current source/controller/service ownership, database ledger/fresh backup,
   independently verified recovery and rollback receipts, then controlled paired
   activation and authenticated UAT. Preserve active Sprint2 until those pass.

No live MTBF/MTTR publication, background evaluation, export, scheduler, production
source request, acquisition/backfill or framework migration is planned implicitly.
Legacy KPIs retain their exact earlier meanings until a separately reviewed change.

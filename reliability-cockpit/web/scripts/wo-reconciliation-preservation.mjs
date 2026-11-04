// NADI-WO-DATA-AND-EXECUTIVE-RECONCILIATION-01: immutable reviewed bytes.
// Validation only: immutable anchor; no pin regeneration or skipped gates.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const reviewedHead="a3f477daa2e47e533a72b23b8fed17b32f1d7226";
const wrapperBase="fb4ca2389f96260a938911f00d5524815807e326";
const fenceBase='988af8d4875758b300e7b563c0a205f143ee184c';
const expectedPaths=[
  ".github/workflows/nadi-engineering-candidate.yml",
  "deploy/development/wo_integrated_controller.py",
  "deploy/development/wo_integrated_grants.py",
  "deploy/development/wo_integrated_source_admission.py",
  "maximo-collector/README.md",
  "maximo-collector/docs/wo-actual-date-recovery.md",
  "maximo-collector/postgres_tests/test_wo_actual_date_postgres.py",
  "maximo-collector/postgres_tests/test_wo_detail_postgres.py",
  "maximo-collector/src/adapters/maximo/actual_dates.py",
  "maximo-collector/src/adapters/maximo/canonical_mappers.py",
  "maximo-collector/src/adapters/maximo/mappers.py",
  "maximo-collector/src/adapters/maximo/oslc_client.py",
  "maximo-collector/src/adapters/maximo/wo_detail.py",
  "maximo-collector/src/api/app.py",
  "maximo-collector/src/repositories/store.py",
  "maximo-collector/src/services/local_mart_projector.py",
  "maximo-collector/src/services/mart.py",
  "maximo-collector/src/services/wo_actual_date_completeness.py",
  "maximo-collector/src/services/wo_actual_date_journal.py",
  "maximo-collector/src/services/wo_actual_date_recovery.py",
  "maximo-collector/src/services/wo_detail_reprojection.py",
  "maximo-collector/tests/test_wo_actual_date_rollback.py",
  "maximo-collector/tests/test_wo_actual_dates.py",
  "maximo-collector/tests/test_wo_detail_reconciliation.py",
  "reliability-cockpit/src/api/reliability.py",
  "reliability-cockpit/src/repositories/mart_reader.py",
  "reliability-cockpit/src/services/registered_maintenance_overview.py",
  "reliability-cockpit/src/services/wo_detail.py",
  "reliability-cockpit/src/services/wo_evidence_sql.py",
  "reliability-cockpit/src/services/wo_overview.py",
  "reliability-cockpit/tests/test_reliability_mart.py",
  "reliability-cockpit/tests/test_wo_detail.py",
  "reliability-cockpit/tests/test_wo_executive_postgres.py",
  "reliability-cockpit/tests/test_wo_executive_reconciliation.py",
  "reliability-cockpit/tests/test_wo_integrated_source_admission.py",
  "reliability-cockpit/web/components/ExecutiveOverview.tsx",
  "reliability-cockpit/web/components/ScopedExecutiveOverview.tsx",
  "reliability-cockpit/web/components/WoEvidenceOverview.tsx",
  "reliability-cockpit/web/components/WorkOrderSourceDetail.tsx",
  "reliability-cockpit/web/lib/api.ts",
  "reliability-cockpit/web/lib/factual-read-contract.ts",
  "reliability-cockpit/web/lib/factual-scoped-reader.ts",
  "reliability-cockpit/web/lib/wo-evidence-types.ts",
  "reliability-cockpit/web/lib/wo-overview.ts",
  "reliability-cockpit/web/scripts/wo-detail-check.mjs",
  "reliability-data-contracts/mappings/maximo-to-contracts.md",
  "reliability-data-contracts/schemas/maintenance-event.schema.json"
];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const wrapper='reliability-cockpit/web/scripts/wo-sr-preservation.mjs';
const importAnchor="import {reviewedFactualReadHashes} from './factual-read-preservation.mjs';";
const importAddition="import {reviewedWoReconciliationHashes} from './wo-reconciliation-preservation.mjs';";
const mapAnchor='const current={...exceptions,...reviewedWoDetailHashes,...reviewedFactualReadHashes};';
const mapAmendment='const current={...exceptions,...reviewedWoDetailHashes,...reviewedFactualReadHashes,...reviewedWoReconciliationHashes(root)};';
export function reviewedWoReconciliationHashes(root){
 const bytes=readFileSync(new URL('./wo-reconciliation-preservation.json',import.meta.url));
 assert.equal(sha(bytes),'b17b9c3ed0e043cb9ce8a8297b9ad88b38746ec95f4140e5614519ea82e77cfc','reviewed WO reconciliation manifest changed');
 const data=JSON.parse(bytes.toString('utf8'));
 assert.equal(bytes.toString('utf8'),JSON.stringify(data,null,2)+'\n','canonical manifest only; duplicate keys prohibited');
 assert.deepEqual(Object.keys(data),['schemaVersion','reviewedHead','fenceBase','files']);
 assert.equal(data.schemaVersion,1);assert.equal(data.reviewedHead,reviewedHead);assert.equal(data.fenceBase,fenceBase);
 assert.deepEqual(Object.keys(data.files),expectedPaths,'finite independently reviewed path inventory only');
 const git=(...args)=>execFileSync('git',['-C',root,...args]);
 assert.equal(git('merge-base',fenceBase,reviewedHead).toString('utf8').trim(),fenceBase);
 for(const [path,hash] of Object.entries(data.files)){
  assert(!path.startsWith('/')&&!path.split('/').includes('..')&&!/[\\*?]/.test(path),'exact relative path only');
  assert.match(hash,/^[a-f0-9]{64}$/);
  assert.equal(sha(git('show',reviewedHead+':'+path)),hash,'reviewed immutable source mismatch: '+path);
 }
 // Preserve the historical wrapper self-pin through a separately reviewed,
 // exact two-line amendment. All historical assertions remain byte-identical.
 const original=git('show',wrapperBase+':'+wrapper).toString('utf8');
 for(const anchor of [importAnchor,mapAnchor])assert.equal(original.split(anchor).length,2,'single exact guard amendment required');
 const expected=original.replace(importAnchor,importAnchor+'\n'+importAddition).replace(mapAnchor,mapAmendment);
 assert.equal(readFileSync(root+'/'+wrapper,'utf8'),expected,'unreviewed preservation wrapper mutation');
 return {...data.files,[wrapper]:sha(expected)};
}

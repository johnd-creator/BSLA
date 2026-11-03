// Closed NADI-ASSET-HIERARCHY-LOCAL-RELEASE-01 source exceptions.
// Earlier classification/WO-detail/Factual/hierarchy ledgers are retained verbatim.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
export const reviewedLocalReleaseHashes=JSON.parse(readFileSync(new URL('./hierarchy-release-preservation.json',import.meta.url),'utf8'));
const expected=[
  ".github/workflows/nadi-engineering-candidate.yml",
  "deploy/development/hierarchy_release_controller.py",
  "deploy/development/hierarchy_source_admission.py",
  "deploy/development/local_development.py",
  "reliability-cockpit/src/services/asset_hierarchy.py",
  "reliability-cockpit/src/services/factual_read_entitlements.py",
  "reliability-cockpit/tests/test_asset_hierarchy.py",
  "reliability-cockpit/tests/test_factual_read_controller.py",
  "reliability-cockpit/tests/test_factual_read_entitlements.py",
  "reliability-cockpit/tests/test_hierarchy_source_admission.py",
  "reliability-cockpit/web/components/AssetHierarchy.tsx",
  "reliability-cockpit/web/eslint.config.mjs",
  "reliability-cockpit/web/lib/asset-hierarchy.ts",
  "reliability-cockpit/web/lib/factual-gateway.ts",
  "reliability-cockpit/web/lib/factual-hierarchy-reader.ts",
  "reliability-cockpit/web/lib/factual-read-contract.ts",
  "reliability-cockpit/web/lib/factual-read-policy.ts",
  "reliability-cockpit/web/package.json",
  "reliability-cockpit/web/scripts/asset-hierarchy-browser.mjs",
  "reliability-cockpit/web/scripts/asset-hierarchy-check.mjs",
  "reliability-cockpit/web/scripts/factual-read-preservation.mjs",
  "reliability-cockpit/web/scripts/hierarchy-release-preservation.mjs"
];
assert.deepEqual(Object.keys(reviewedLocalReleaseHashes).sort(),expected,'closed local-release source inventory');
for(const hash of Object.values(reviewedLocalReleaseHashes))assert.match(hash,/^[a-f0-9]{64}$/);

// Finite source exceptions for NADI-ASSET-HIERARCHY-01; no grant/controller/source write.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
export const reviewedHierarchyHashes=JSON.parse(readFileSync(new URL('./asset-hierarchy-preservation.json',import.meta.url),'utf8'));
const expected=[
  ".github/workflows/nadi-engineering-candidate.yml",
  "reliability-cockpit/src/api/reliability.py",
  "reliability-cockpit/src/services/asset_hierarchy.py",
  "reliability-cockpit/tests/test_asset_hierarchy.py",
  "reliability-cockpit/web/app/(workspace)/assets/[...canonicalId]/page.tsx",
  "reliability-cockpit/web/components/AssetHierarchy.tsx",
  "reliability-cockpit/web/eslint.config.mjs",
  "reliability-cockpit/web/lib/api.ts",
  "reliability-cockpit/web/lib/asset-hierarchy.ts",
  "reliability-cockpit/web/lib/factual-gateway.ts",
  "reliability-cockpit/web/package.json",
  "reliability-cockpit/web/scripts/asset-evidence-preservation.mjs",
  "reliability-cockpit/web/scripts/asset-hierarchy-browser.mjs",
  "reliability-cockpit/web/scripts/asset-hierarchy-check.mjs",
  "reliability-cockpit/web/scripts/asset-hierarchy-preservation.mjs",
  "reliability-cockpit/web/scripts/factual-read-preservation.mjs",
  "reliability-cockpit/web/scripts/hierarchy-entry.tsx"
];
assert.deepEqual(Object.keys(reviewedHierarchyHashes).sort(),expected,'finite hierarchy source inventory');
for(const hash of Object.values(reviewedHierarchyHashes))assert.match(hash,/^[a-f0-9]{64}$/);

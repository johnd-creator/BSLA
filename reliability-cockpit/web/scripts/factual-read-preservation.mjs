import {reviewedLocalReleaseHashes} from './hierarchy-release-preservation.mjs';
// Exact owner-authorized revised-task exceptions, reviewed independently at delivery.
// Existing account/demo/Engineering/source/production-CI protection pins stay active.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {reviewedHierarchyHashes} from './asset-hierarchy-preservation.mjs';
const historicalBytes=readFileSync(new URL('./factual-read-preservation.json',import.meta.url));
assert.equal(createHash('sha256').update(historicalBytes).digest('hex'),'1b28e8061c9f07de5ce839108bfd38502cf87140c0567282a5da3e5d7ab56def','PR120 historical READ pins remain unchanged');
const historicalFactualReadHashes=JSON.parse(historicalBytes.toString('utf8'));
export const reviewedFactualReadHashes={...historicalFactualReadHashes,...reviewedHierarchyHashes,...reviewedLocalReleaseHashes};
for(const [name,hash] of Object.entries(reviewedFactualReadHashes)){
 assert(!name.startsWith('/')&&!name.split('/').includes('..'),'relative reviewed source only');
 assert.match(hash,/^[a-f0-9]{64}$/);
}

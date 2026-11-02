// Exact owner-authorized revised-task exceptions, reviewed independently at delivery.
// Existing account/demo/Engineering/source/production-CI protection pins stay active.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
export const reviewedFactualReadHashes=JSON.parse(readFileSync(new URL('./factual-read-preservation.json',import.meta.url),'utf8'));
for(const [name,hash] of Object.entries(reviewedFactualReadHashes)){
 assert(!name.startsWith('/')&&!name.split('/').includes('..'),'relative reviewed source only');
 assert.match(hash,/^[a-f0-9]{64}$/);
}

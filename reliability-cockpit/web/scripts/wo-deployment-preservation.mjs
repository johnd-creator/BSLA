// Exact operational correction reviewed with the linked immutable source.
// Historical47-path reconciliation/classification/factual pins are unchanged.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const reviewedHead="f1917628acb9cc285f09d8667fb66f70a0bf824a";
const files={
  ".github/workflows/nadi-engineering-candidate.yml": "416d4b990a731eb2b2e4bb294a7c5637808781d1ec61374e3b3643bc33cb3b90",
  "DEV-LOG.md": "4934c9a6f550872179fd85c915745358f17899b87019768d1ee98fce8c56c4e2",
  "deploy/development/wo-service-rehearsal-graph.json": "63bf00d768ba5b814346bfcf0a02daf66d0958ef8efc11ff840b6197a423054a",
  "deploy/development/wo_service_activation.py": "a64d40c8b387941e4f02b25c1c5144b61ea64d450cfa02962833cf39136a5042",
  "deploy/development/wo_service_rehearsal.py": "10dbd81c66e7e2e5f0c148a672b899841b2efb053c603420b3a47e4fa60adb33",
  "plans/REPOSITORY-STATUS.md": "aa2f25e52f5a395fe83e6b2a64ce17938c34e61b0e6519a8272759093a4ee216",
  "reliability-cockpit/docs/NADI-WO-ACTIVATION-CORRECTION-01.md": "8fbf5e3a13b58593e08442267bb263043a353686ae9a62f79bc1f349d56d9d9d",
  "reliability-cockpit/tests/test_wo_service_activation.py": "8fa5dc005f5ae071308af5fb95af04a220b358a18f080287d9929a22849530ff"
};
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export function reviewedWoDeploymentHashes(root){
 const git=(...args)=>execFileSync('git',['-C',root,...args]);
 assert.equal(git('merge-base',reviewedHead,'HEAD').toString('utf8').trim(),reviewedHead);
 for(const [path,expected] of Object.entries(files)){
  assert(!path.startsWith('/')&&!path.split('/').includes('..')&&!/[\\*?]/.test(path));
  assert.equal(hash(git('show',reviewedHead+':'+path)),expected,'immutable deployment correction pin changed: '+path);
  assert.equal(hash(readFileSync(root+'/'+path)),expected,'unreviewed deployment correction change: '+path);
 }
 // The old loader and all of its historical assertions survive an exact
 // import/return amendment; neither the old manifest nor wrapper is rewritten.
 const loader='reliability-cockpit/web/scripts/wo-reconciliation-preservation.mjs';
 const original=git('show',reviewedHead+':'+loader).toString('utf8');
 const anchor="import assert from 'node:assert/strict';";
 const before='return {...data.files,[wrapper]:sha(expected)};';
 const after='return {...data.files,...reviewedWoDeploymentHashes(root),[wrapper]:sha(expected)};';
 for(const value of [anchor,before])assert.equal(original.split(value).length,2);
 const expected=original.replace(anchor,"import {reviewedWoDeploymentHashes} from './wo-deployment-preservation.mjs';\n"+anchor).replace(before,after);
 assert.equal(readFileSync(root+'/'+loader,'utf8'),expected,'unreviewed historical loader amendment');
 return files;
}

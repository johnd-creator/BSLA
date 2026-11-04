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
const repairedHead="a70a0f3043b5a57ba6f23e36a27de0c8e2b90201";
const repairedFiles={
  "deploy/development/wo_service_activation.py": "d35eeb958187c0bd80819da094668cf646b36513b417660f51eda47553fc460c",
  "reliability-cockpit/docs/NADI-WO-ACTIVATION-CORRECTION-01.md": "465bb4406e136ef7b508446cbab59492a4f48008876bb87ed3e6f1c1b1fcd1f6",
  "reliability-cockpit/tests/test_wo_service_activation.py": "117c9e62eca964a1d0cc66de5bcfe0f56872531beadcee71062ed7e22be1430a"
};
const labelBaseHead="244686244bb39ab8e7a929a52f2a39940b4bb1b9";
const labelReviewedHead="3d68eef4f88356b3bf515bbaa2ee1e90c182d027";
const labelFiles={
  "DEV-LOG.md": "0b37fc6b80f44cd9d2a34b03fbf4409fb45da56bc17a3eff82e7656d2a4b4b0d",
  "deploy/development/wo_service_activation.py": "2beb02efe4616d1736bfc2750991e7e97e4253133f1e8da32da5258de8376711",
  "deploy/development/wo_service_rehearsal.py": "6b72686de268a221e027e06f52e31c79610cb3deb5889798bfd323992164eac3",
  "plans/REPOSITORY-STATUS.md": "fd04a466c1e405f107fab156f51886379d7e05e01e81ef0b221ea3f7663f80f9",
  "reliability-cockpit/docs/NADI-WO-ACTIVATION-CORRECTION-01.md": "7e8c412dcfbf7d84f3f5406c3cfc05963eeb89c2edba647ed189abad26c21b50",
  "reliability-cockpit/tests/test_wo_service_activation.py": "9be92ddbe9544632861c0bd0528c763d5d2004734773b3b385f121e779867de6"
};
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export function reviewedWoDeploymentHashes(root){
 const git=(...args)=>execFileSync('git',['-C',root,...args]);
 assert.equal(git('merge-base',reviewedHead,'HEAD').toString('utf8').trim(),reviewedHead);
 for(const [path,expected] of Object.entries(files)){
  assert(!path.startsWith('/')&&!path.split('/').includes('..')&&!/[\\*?]/.test(path));
  assert.equal(hash(git('show',reviewedHead+':'+path)),expected,'immutable deployment correction pin changed: '+path);
 }
 assert.equal(git('merge-base',repairedHead,'HEAD').toString('utf8').trim(),repairedHead);
 for(const [path,expected] of Object.entries(repairedFiles)){
  assert(Object.hasOwn(files,path),'repair outside reviewed deployment path set');
  assert.equal(hash(git('show',repairedHead+':'+path)),expected,'immutable predecessor repair pin changed: '+path);
 }
 assert.equal(git('merge-base',labelBaseHead,'HEAD').toString('utf8').trim(),labelBaseHead);
 assert.equal(hash(git('show',labelBaseHead+':reliability-cockpit/web/scripts/wo-deployment-preservation.mjs')),"0ec2de05b0677e774c361467cd12cc1d73f4f8927e332af39936ae7a6f5edcbf",'immutable predecessor deployment loader changed');
 assert.equal(git('merge-base',labelReviewedHead,'HEAD').toString('utf8').trim(),labelReviewedHead);
 for(const [path,expected] of Object.entries(labelFiles)){
  assert(Object.hasOwn(files,path),'label correction outside original deployment path set');
  assert.equal(hash(git('show',labelReviewedHead+':'+path)),expected,'immutable image-label correction pin changed: '+path);
 }
 const current={...files,...repairedFiles,...labelFiles};
 for(const [path,expected] of Object.entries(current))assert.equal(hash(readFileSync(root+'/'+path)),expected,'unreviewed deployment correction change: '+path);
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
 return current;
}

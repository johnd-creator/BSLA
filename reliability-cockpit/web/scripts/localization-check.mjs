import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,readFileSync,rmSync,symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
const require=createRequire(import.meta.url),ts=require('typescript');
const temp=mkdtempSync(join(tmpdir(),'nadi-id-'));let checks=0;
const check=(name,fn)=>{fn();checks++;console.log('PASS '+name);};
try {
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/id-copy.ts','lib/glossary.ts','--outDir',temp,'--rootDir','.','--module','commonjs','--target','ES2022','--jsx','react-jsx','--esModuleInterop','--resolveJsonModule','--moduleResolution','node','--skipLibCheck'],{stdio:'pipe'});
 symlinkSync(resolve('node_modules'),join(temp,'node_modules'));
 const {idText,statusLabel,errorLabel}=require(join(temp,'lib/id-copy.js'));
 const {glossary,searchGlossary}=require(join(temp,'lib/glossary.js'));
 const messages=JSON.parse(readFileSync('lib/id-messages.json','utf8'));
 check('all dictionary entries are nonblank and retain technical placeholder codes',()=>{for(const [key,value] of Object.entries(messages)){assert.ok(key.trim()&&value.trim(),key);assert.ok(!/[\uFFFD]/.test(value),key);}});
 check('UNKNOWN and NOT ASSESSED are distinct neutral presentation states',()=>{assert.equal(statusLabel('UNKNOWN'),'Belum diketahui (UNKNOWN)');assert.equal(statusLabel('NOT_ASSESSED'),'Belum dinilai (NOT_ASSESSED)');assert.equal(statusLabel(null),'—');assert.equal(statusLabel('DEMO_VENDOR_STATE'),'DEMO_VENDOR_STATE');});
 check('approval, receipt and local completion never authorize work',()=>{assert.equal(statusLabel('APPROVED'),'Rekam disetujui (APPROVED)');assert.match(statusLabel('ACK'),/penerimaan/);assert.match(statusLabel('COMPLETED'),/lokal/);assert.notEqual(statusLabel('COMPLETED'),statusLabel('VERIFIED'));});
 check('errors retain exact security/conflict code without leaking transport details',()=>{for(const code of ['REVISION_CONFLICT','ACCESS_DENIED','CSRF_DENIED','SESSION_EXPIRED'])assert.ok(errorLabel(code).includes(code));assert.ok(!errorLabel(new Error('https://private/?password=secret')).includes('secret'));assert.equal(errorLabel('Unable to sign in. Check your credentials.'),idText('Unable to sign in. Check your credentials.'));assert.equal(errorLabel(idText('Enter a reviewer reason before a simulated decision.')),idText('Enter a reviewer reason before a simulated decision.')); });
 check('glossary is searchable in both languages and has unique anchors',()=>{assert.equal(new Set(glossary.map(x=>x.id)).size,glossary.length);assert.ok(searchGlossary('pemeliharaan').length);assert.ok(searchGlossary('acknowledgment').length);assert.equal(searchGlossary('   ').length,glossary.length);assert.equal(searchGlossary('no-such-term-1234').length,0);});
 check('candidate method rules remain pending engineer validation',()=>{for(const id of ['vibration','ir','mcsa','tribology','threshold'])assert.ok(glossary.find(x=>x.id===id)?.pending,id);assert.match(glossary.find(x=>x.id==='pd-dga').meaning,/tidak|bukan/);});
 // AUTH-02 reviewed lib/api.ts: only 401 login redirect and scope-denied copy; DTOs and query paths unchanged.
 // Engineering/PdM review: optional v1.2 input_capture, v1.3 work_origin and v1.4 manual analysis/reported SR;
 // Existing authority and legacy wire values stay unchanged; origin has no asset-binding authority.
 // Full typed frozen Case evidence;
 // useQaRecords generation fences, synchronous revocation clearing, bounded inspection pages.
 // Native wire values, server-side authority, remaining fixtures and V2 tokens stay pinned.
 const immutable={
  "lib/api.ts": "a56c03c8fefa538fc87ed30faa4614d0633e5b2a13e6726586dc97f14e68c5e0",
  "lib/product-records.ts": "6d3fe024d757efe944d48a03a93ddac5a2da657c37613ea7b9b4108cb87cf282",
  "lib/case-records.ts": "1c224aca34185314db8daeb7c21aa2e095e28c35d4b2d419460162315fa31456",
  "lib/advisory-records.ts": "d1edee16e4d68b70d9657bf9787d50f65bae62db103c3937d6f91ba5f94f779a",
  "lib/engineering.ts": "f1303806007546d0c107055c888a87d0b0f83852c89cffaa94f45bac3cf558f6",
  "lib/engineering-workflow.ts": "768dead1b6102602010553e9f687af25c65c537cf641965a6190baa7c3cacecf",
  "lib/manual-pdm.ts": "22cda16071d8d0912867397cdf916fa4bcb86cb325ecd3eeff3aac6d77aae5be",
  "lib/engineering-http.ts": "1090f7dc3d151c2a790cb954fab9d0f285972321204db0e5dd7ca3873308c5e8",
  "lib/bounded-http.ts": "3c1e79bf7fbb6ae3e9735695c3f944ee4abca87fe20d132c0139e34fa61b813e",
  // Sprint2: exact reviewed configurable bounded read hook; auth/clearing still regression-tested.
  "components/useQaRecords.ts": "59b015a5ae8fc7a57e352f4b16d3ab4855e10bdc8db629c2429ae4c45cba039c",
  "app/api/engineering-qa/[...path]/route.ts": "460aec726cbc10a39de4a6d6c817e1d3fcacda63697b7ce3fd52d46a5856d0b3",
  "fixtures/ux-bundle-b.json": "aac1b608ec2b0ba9e0c99d6293b8c8bb016a3422f3a8e9eedc4118e535d8b061",
  "app/design-tokens.css": "b704e75acb8c61ca2574287dba45a2b929d0823e5d3f57f20b4ceb870736e73a"
};
 check('reviewed Engineering/PdM contracts, session handling, fixture values and V2 tokens retain pinned hashes',()=>{for(const [file,hash] of Object.entries(immutable))assert.equal(createHash('sha256').update(readFileSync(file)).digest('hex'),hash,file);});
 check('synthetic screen selection uses original keys independently of translated labels',()=>{for(const [file,variable] of [['components/EngineeringWorkflow.tsx','views'],['components/Phase2Workspace.tsx','screens']]){const source=readFileSync(file,'utf8');const declaration=source.match(new RegExp('const '+variable+'=([^;]+);'))[1];assert.ok(!declaration.includes('idText'));assert.doesNotMatch(source,/changeView\(idText|useState<Screen>\(idText|quantity,setQuantity\]=useState\(idText/);assert.ok(source.includes('idText('+ (variable==='views'?'x':'name')+')'));}});
 check('original reasons are preserved in synthetic command history',()=>{const source=readFileSync('components/EngineeringWorkflow.tsx','utf8');for(const reason of ['Demo workflow','Submitted demo finding','Local demo follow-up'])assert.ok(source.includes('"'+reason+'"')&&!source.includes('idText("'+reason+'")'));});
 check('translated option labels always carry a separate original value',()=>{for(const file of ['components/CaseForm.tsx','components/AdvisoryWorkspace.tsx','components/RecommendationWorkspace.tsx','components/EngineeringWorkspace.tsx']){const source=readFileSync(file,'utf8'),sf=ts.createSourceFile(file,source,99,true,ts.ScriptKind.TSX);function visit(n){if(ts.isJsxElement(n)&&n.openingElement.tagName.getText(sf)==='option'&&n.children.some(c=>c.getText(sf).includes('statusLabel(')))assert.ok(n.openingElement.attributes.properties.some(a=>a.name?.text==='value'),file);ts.forEachChild(n,visit);}visit(sf);}});
 console.log(`Indonesian localization checks passed: ${checks}; dictionary=${Object.keys(messages).length}, glossary=${glossary.length}`);
} finally {rmSync(temp,{recursive:true,force:true});}

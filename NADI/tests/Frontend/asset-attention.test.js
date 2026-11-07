import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=(name)=>readFileSync(new URL(`../../${name}`,import.meta.url),'utf8');
const board=read('resources/views/priorities/board.blade.php');
const form=read('resources/views/priorities/form.blade.php');
const css=read('resources/css/asset-attention.css');
test('attention separates engineer judgment from unassessed clues without risk meters',()=>{
 assert.match(board,/Prioritas yang sudah dinilai/);assert.match(board,/Kandidat yang belum dinilai/);
 assert.match(board,/WO berulang bukan failure berulang/);assert.match(board,/hanya Registry BSR \/ IP/);
 assert.match(board,/Jumlah dan kondisi aset tidak diketahui/);assert.match(board,/Daftar kosong bukan berarti aset sehat/);
 assert.doesNotMatch(board,/<meter|<progress/);
});
test('judgment has labelled fields, cancel, idempotency and version protection',()=>{
 for(const field of ['urgency','owner','due_on','review_on','disruption_id','inspection_id','work_order_ref','change_reason']) {
  assert.ok(form.includes(`for="${field}"`)); assert.ok(form.includes(`name="${field}"`));
 }
 assert.match(form,/name="request_key"/);assert.match(form,/name="version"/);assert.match(form,/>Batal</);
 assert.match(form,/minlength="5" maxlength="2000" required/);
});
test('attention stays compact with contained mobile tables and visible text urgency',()=>{
 assert.match(css,/overflow-wrap: anywhere/);assert.match(css,/@media \(max-width: 700px\)/);
 assert.match(css,/min-height: 44px/);assert.match(board,/AssetPriority::URGENCIES/);
});

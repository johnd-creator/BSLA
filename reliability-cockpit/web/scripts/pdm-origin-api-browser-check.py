"""Actual PdM components → real trusted-session API → temporary PostgreSQL.

All browser URLs fulfilled before network, including the .invalid origin.
No TLS ignore options, real browser profile, active service or operational DB.
"""
import argparse,json,os,sys,traceback
from pathlib import Path
from urllib.parse import unquote,urlparse
from playwright.sync_api import sync_playwright
sys.path[:0]=['.','tests']
from test_bundle_c_integration import BundleCPostgresIntegrationTest

p=argparse.ArgumentParser()
for key in ('bundle','css','report'):p.add_argument('--'+key,type=Path,required=True)
p.add_argument('--chromium',type=Path)
a=p.parse_args();assert os.environ.get('NADI_APPLICATION_TEST_DSN'),'Hermetic PostgreSQL fixture required'
f=BundleCPostgresIntegrationTest('test_complete_trusted_http_workflow_preserves_lineage');f.setUp()
ORIGIN='https://nadi.example.invalid';results=[];writes=[];errors=[];escaped=[];lost_ack=True
ANALYSIS=dict(notes='  Synthetic manual reasoning\nOriginal 0 remains 0  ',recommended_follow_up='Synthetic engineer follow-up',provenance='HUMAN_ENTERED_ENGINEER_NOTES')
SR=dict(sr_number='  00012/SYNTHETIC  ',follow_up_note='Synthetic SR follow-up; not checked',system='MAXIMO',verification='REPORTED_UNVERIFIED')
try:
 token,csrf=f.credentials['author'];f.client.cookies.set(f.authority.COOKIE,token)
 identity=dict(subject='author',username='synthetic-author',roles=['AUTHOR'],asset_ids=[f.asset],csrf_token=csrf)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,**({'executable_path':str(a.chromium)} if a.chromium else {}))
  context=browser.new_context(viewport=dict(width=1440,height=1000));page=context.new_page();page.set_default_timeout(15000)
  page.on('pageerror',lambda e:errors.append(str(e)))
  def respond(route):
   global lost_ack
   req=route.request;path=unquote(urlparse(req.url).path)
   if not req.url.startswith(ORIGIN+'/'):escaped.append(req.url);route.abort();return
   if req.is_navigation_request():
    route.fulfill(content_type='text/html; charset=utf-8',body='<html><head><meta charset="utf-8"><style>'+a.css.read_text()+'#pdm-fixture-diagnostics{display:none}</style></head><body><div id="root"></div><script>window.fixtureIdentity='+json.dumps({k:v for k,v in identity.items() if k!='csrf_token'})+'</script><script src="/candidate.js"></script></body></html>');return
   if path=='/candidate.js':route.fulfill(content_type='application/javascript',body=a.bundle.read_text());return
   if path=='/api/engineering-qa/session':route.fulfill(json=identity);return
   if path.startswith('/api/engineering-qa/'):
    suffix=req.url[len(ORIGIN+'/api/engineering-qa/'):]
    f.client.cookies.set(f.authority.COOKIE,f.credentials[identity['subject']][0])
    body=req.post_data_json if req.method in ('POST','PUT') else None
    response=f.client.request(req.method,'/v1/engineering/'+suffix,json=body,headers={'Origin':ORIGIN,'X-CSRF-Token':req.headers.get('x-csrf-token','')})
    if req.method in ('POST','PUT'):
     writes.append(dict(method=req.method,body=body,status=response.status_code))
    if req.method=='POST' and suffix=='inspections' and lost_ack and response.status_code==201:
     lost_ack=False;route.fulfill(status=503,json={'detail':{'code':'QA_BACKEND_UNAVAILABLE'}});return
    route.fulfill(status=response.status_code,content_type='application/json',body=response.content);return
   escaped.append(req.url);route.abort()
  context.route('**/*',respond);page.goto(ORIGIN+'/pdm')
  page.get_by_role('button',name='Input Pengukuran',exact=True).click()
  page.get_by_label('Asal pekerjaan',exact=True).select_option('DEPARTMENT_REQUEST')
  page.get_by_label('Bidang peminta',exact=True).fill('  Synthetic EPA  ')
  page.get_by_label('Label aset pada permintaan / temuan (opsional)',exact=True).fill('  Conveyor tak terverifikasi  ')
  page.get_by_label('Catatan analisis engineer (manual)',exact=True).fill(ANALYSIS['notes'])
  page.get_by_label('Saran tindak lanjut engineer (manual, opsional)',exact=True).fill(ANALYSIS['recommended_follow_up'])
  page.get_by_role('button',name='Tambah referensi SR',exact=True).click()
  page.get_by_label('Nomor SR 1',exact=True).fill(SR['sr_number'])
  page.get_by_label('Catatan tindak lanjut SR 1 (opsional)',exact=True).fill(SR['follow_up_note'])
  page.get_by_label('Versi metode / prosedur',exact=True).fill('synthetic-origin-ui-1')
  page.get_by_label('Parameter 1',exact=True).fill('Synthetic velocity')
  page.get_by_label('Tipe nilai 1',exact=True).select_option('NUMERIC')
  page.get_by_label('Nilai asli 1',exact=True).fill('0')
  page.get_by_label('Titik 1',exact=True).fill('point:SYNTHETIC')
  page.get_by_label('Unit asli 1',exact=True).fill('mm/s')
  page.get_by_label('Waktu measurement 1',exact=True).fill('2026-10-08T09:31:17+07:00')
  page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
  page.wait_for_function('document.querySelector("[role=alert]")')
  assert page.get_by_label('Bidang peminta',exact=True).input_value()=='  Synthetic EPA  '
  page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
  page.locator('.product-record-detail').wait_for()
  assert len(writes)==2 and writes[0]['body']==writes[1]['body']
  rows=f.call('GET','inspections')['items'];assert len(rows)==1
  row=rows[0];record=row['record_id'];origin=dict(source='DEPARTMENT_REQUEST',requesting_department='  Synthetic EPA  ',reported_asset_label='  Conveyor tak terverifikasi  ')
  assert row['contract_version']=='1.4'
  assert row['engineering_analysis']==ANALYSIS and row['sr_references']==[SR]
  assert row['field_approval']=='ENGINEER_FIELDS_PENDING'
  assert row['contract_version']=='1.4' and row['work_origin']==origin and row['measurements'][0]['value']==0
  assert row['canonical_asset_id']==f.asset
  results.append(dict(scenario='package1–3 native department+manual analysis+unverified SR actual form → real API/PG → committed503/retry same intent → one saved record/detail',status='PASS'))
  page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
  assert page.get_by_label('Bidang peminta',exact=True).input_value()=='  Synthetic EPA  '
  assert page.get_by_label('Catatan analisis engineer (manual)',exact=True).input_value()==ANALYSIS['notes']
  assert page.get_by_label('Nomor SR 1',exact=True).input_value()==SR['sr_number']
  page.get_by_label('Catatan analisis engineer (manual)',exact=True).fill('Synthetic revised analysis')
  page.get_by_label('Catatan tindak lanjut SR 1 (opsional)',exact=True).fill('Synthetic revised follow-up; still unverified')
  page.get_by_label('Asal pekerjaan',exact=True).select_option('PDM_PM_52_WEEK')
  assert page.get_by_label('Bidang peminta',exact=True).count()==0
  page.get_by_label('Label aset pada permintaan / temuan (opsional)',exact=True).fill('Synthetic PM finding asset label')
  page.get_by_role('button',name='Simpan revisi draf',exact=True).click()
  page.locator('.product-record-detail').get_by_text('Temuan PdM · PM 52 week',exact=True).wait_for()
  revised=f.call('GET','inspections/'+record)
  assert revised['revision']==2 and revised['work_origin']==dict(source='PDM_PM_52_WEEK',reported_asset_label='Synthetic PM finding asset label')
  history=f.call('GET','inspections/'+record+'/history')
  assert len(history)==2 and history[0]['snapshot']['work_origin']==origin and history[1]['snapshot']['work_origin']==revised['work_origin']
  assert history[0]['snapshot']['engineering_analysis']==ANALYSIS and history[0]['snapshot']['sr_references']==[SR]
  assert revised['engineering_analysis']['notes']=='Synthetic revised analysis'
  assert revised['sr_references'][0]['verification']=='REPORTED_UNVERIFIED'
  assert revised['sr_references'][0]['follow_up_note']=='Synthetic revised follow-up; still unverified'
  assert f.call('GET','recommendations')['items']==[]
  page.get_by_role('button',name='Baca riwayat',exact=True).click()
  page.get_by_text('Baca isi revisi 1',exact=True).click()
  page.get_by_role('cell').filter(has=page.get_by_text('Baca isi revisi 1',exact=True)).get_by_text(ANALYSIS['notes'],exact=True).wait_for()
  page.get_by_role('cell').filter(has=page.get_by_text('Baca isi revisi 1',exact=True)).get_by_text('  Synthetic EPA  ',exact=True).wait_for()
  page.get_by_role('button',name='Revisi berikutnya',exact=True).click()
  page.get_by_text('Baca isi revisi 2',exact=True).click()
  page.get_by_role('cell').filter(has=page.get_by_text('Baca isi revisi 2',exact=True)).get_by_text('Synthetic revised analysis',exact=True).wait_for()
  page.get_by_role('cell').filter(has=page.get_by_text('Baca isi revisi 2',exact=True)).get_by_text('Temuan PdM · PM 52 week',exact=True).wait_for()
  results.append(dict(scenario='actual native editor readback → PM52 conditional fields → real CAS revision → immutable origin/analysis/SR history rendered per revision',status='PASS'))
  page.screenshot(path=str(a.report.with_name('pdm-package-api-desktop.png')),full_page=True)
  page.set_viewport_size(dict(width=390,height=844))
  page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
  assert page.get_by_label('Asal pekerjaan',exact=True).input_value()=='PDM_PM_52_WEEK'
  assert page.get_by_label('Catatan analisis engineer (manual)',exact=True).input_value()=='Synthetic revised analysis'
  assert page.get_by_label('Nomor SR 1',exact=True).input_value()==SR['sr_number']
  assert page.get_by_label('Aset kanonis berotorisasi').is_disabled()
  page.get_by_label('Asal pekerjaan',exact=True).scroll_into_view_if_needed()
  page.screenshot(path=str(a.report.with_suffix('.png')),full_page=True)
  assert not errors and not escaped
  results.append(dict(scenario='390px real component form reopens persisted PM52+analysis+SR with fixed authorized asset, no department or operator dependency',status='PASS'))
  page.get_by_label('Catatan analisis engineer (manual)',exact=True).fill('')
  page.get_by_label('Saran tindak lanjut engineer (manual, opsional)',exact=True).fill('')
  page.get_by_role('button',name='Hapus referensi SR 1',exact=True).click()
  page.get_by_label('Asal pekerjaan',exact=True).select_option('')
  page.get_by_role('button',name='Simpan revisi draf',exact=True).click()
  page.locator('.product-record-detail').get_by_text('Belum ada catatan analisis manual pada revisi ini.',exact=True).wait_for()
  cleared=f.call('GET','inspections/'+record)
  assert cleared['revision']==3 and cleared['contract_version']=='1.1'
  assert not any(key in cleared for key in ('work_origin','engineering_analysis','sr_references'))
  final_history=f.call('GET','inspections/'+record+'/history')
  assert len(final_history)==3 and final_history[0]['snapshot']['engineering_analysis']==ANALYSIS
  results.append(dict(scenario='actual editor explicit clear origin/analysis/SR → persisted legacy-native downgrade, previous immutable context retained',status='PASS'))
  # Continue the same actual component, trusted API and disposable PG record.
  original_measurements=cleared['measurements']
  assert original_measurements[0]['value']==0 and original_measurements[0]['unit']=='mm/s'
  assert original_measurements[0]['measured_at']=='2026-10-08T09:31:17+07:00'
  page.set_viewport_size(dict(width=1440,height=1000))
  def as_actor(subject):
   global identity
   principal=f.directory(subject);token,csrf=f.credentials[subject]
   identity=dict(subject=subject,username='synthetic-'+subject,roles=[r.value for r in principal.roles],asset_ids=sorted(principal.asset_ids),csrf_token=csrf)
   f.client.cookies.set(f.authority.COOKIE,token)
   page.goto(ORIGIN+'/pdm?record='+record)
   page.locator('.product-record-detail').wait_for()
  page.get_by_role('button',name='Ajukan inspeksi',exact=True).click()
  page.locator('.product-record-detail').locator('[title=SUBMITTED]').wait_for()
  assert page.get_by_role('button',name='Mulai review independen',exact=True).count()==0
  as_actor('reviewer')
  page.get_by_label('Alasan review / revisi',exact=True).fill('SYNTHETIC independent check')
  page.get_by_role('button',name='Mulai review independen',exact=True).click()
  page.get_by_label('Kembalikan untuk koreksi',exact=True).check()
  page.get_by_label('Alasan review / revisi',exact=True).fill('SYNTHETIC clarify observation; record only')
  page.get_by_role('button',name='Simpan keputusan review',exact=True).click()
  page.locator('.product-record-detail').locator('[title=RETURNED]').wait_for()
  as_actor('author')
  page.get_by_label('Alasan review / revisi',exact=True).fill('SYNTHETIC author clarification')
  page.get_by_role('button',name='Revisi rekam dikembalikan / ditolak',exact=True).click()
  page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
  page.get_by_label('Observasi (satu per baris)',exact=True).fill('SYNTHETIC clarification after independent return')
  page.get_by_role('button',name='Simpan revisi draf',exact=True).click()
  page.get_by_role('button',name='Ajukan inspeksi',exact=True).click()
  page.locator('.product-record-detail').locator('[title=SUBMITTED]').wait_for()
  as_actor('reviewer')
  page.get_by_label('Alasan review / revisi',exact=True).fill('SYNTHETIC second independent check')
  page.get_by_role('button',name='Mulai review independen',exact=True).click()
  assert page.get_by_label('Setujui rekam inspeksi',exact=True).is_checked()==False
  page.get_by_label('Setujui rekam inspeksi',exact=True).check()
  page.get_by_label('Alasan review / revisi',exact=True).fill('SYNTHETIC record accepted; no health or work authorization')
  page.get_by_role('button',name='Simpan keputusan review',exact=True).click()
  page.locator('.product-record-detail').locator('[title=APPROVED]').first.wait_for()
  approved=f.call('GET','inspections/'+record,actor='reviewer')
  assert approved['status']=='APPROVED' and approved['measurements']==original_measurements
  assert f.call('GET','cases')['items']==[], 'normal inspection completion must not create a Case'
  results.append(dict(scenario='actual author submit → independent reviewer begin/return → author revise/update/resubmit → fresh independent APPROVED; originals preserved and zero automatic Cases',status='PASS'))
  as_actor('author')
  page.get_by_role('button',name='Buat Engineering Case',exact=True).click()
  page.locator('#case-title').fill('SYNTHETIC optional formal investigation')
  page.locator('#case-problem').fill('SYNTHETIC unverified finding; not a diagnosis')
  page.get_by_role('button',name='Simpan kasus',exact=True).click()
  page.get_by_text('Evidence versi exact telah ditautkan.',exact=False).wait_for()
  cases=f.call('GET','cases')['items'];assert len(cases)==1
  snapshot=cases[0]['evidence'][0]['snapshot']['reviewed_inspection']
  assert snapshot['revision']==approved['revision'] and snapshot['measurements']==original_measurements
  results.append(dict(scenario='deliberate optional Case only after approved native; real API frozen exact reviewed revision and original measurements',status='PASS'))
  assert not errors and not escaped
  context.close();browser.close()
except Exception:
 results.append(dict(scenario='real API/UI fixture',status='FAIL',trace=traceback.format_exc()))
 raise
finally:
 f.tearDown();a.report.write_text(json.dumps(dict(results=results,scope='actual imported UI + trusted-session FastAPI TestClient + hermetic PostgreSQL; all browser traffic intercepted; no TLS bypass; synthetic fixture identity only',browser_errors=errors,unexpected_requests=escaped,writes=len(writes)),indent=2)+'\n')

"""Actual AuthenticatedWorkspace + actual providers/PdmCenter/Form. All URLs intercepted."""
import argparse
import json
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--bundle',type=Path,required=True)
parser.add_argument('--only',default='')
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--chromium',type=Path)
args=parser.parse_args()
bundle=args.bundle.read_text()
ORIGIN='https://pdm-auth-workspace-fixture.invalid'
INITIAL=dict(subject='local:synthetic-author',username='synthetic-author',roles=['AUTHOR'],asset_ids=['asset:SYNTHETIC:A'],csrf_token='synthetic-not-a-session')
results=[]

def require(value,message):
    if not value:raise AssertionError(message)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'executable_path':str(args.chromium)} if args.chromium else {}))
    def scenario(name,test):
        if args.only and args.only not in name:return
        context=browser.new_context(viewport=dict(width=1440,height=1000))
        page=context.new_page();page.set_default_timeout(10000)
        state=dict(who=dict(INITIAL),hold_session=False,sessions=[],hold_write=False,writes=[],posts=[],records=[],receipts={},escaped=[],navigations=[],errors=[],list_requests=[])
        page.on('pageerror',lambda error:state['errors'].append(str(error)))
        def respond(route):
            request=route.request
            if not request.url.startswith(ORIGIN+'/'):
                state['escaped'].append(request.url);route.abort();return
            from urllib.parse import urlparse,unquote,parse_qs
            path=unquote(urlparse(request.url).path)
            if request.is_navigation_request():
                state['navigations'].append(request.url)
                if path=='/login':route.fulfill(body='<html><head><meta charset="utf-8"></head><h1>Login fixture</h1></html>',content_type='text/html; charset=utf-8');return
                identity={k:v for k,v in state['who'].items() if k!='csrf_token'}
                route.fulfill(body='<html><head><meta charset="utf-8"></head><div id="root"></div><script>window.fixtureIdentity='+json.dumps(identity)+'</script><script src="/candidate.js"></script></html>',content_type='text/html; charset=utf-8');return
            if path=='/candidate.js':route.fulfill(body=bundle,content_type='application/javascript; charset=utf-8');return
            if path=='/api/engineering-qa/session':
                if state['hold_session']:state['sessions'].append(route)
                else:route.fulfill(json=state['who'])
                return
            if path.startswith('/api/engineering-qa/asset-context/'):
                route.fulfill(json=dict(canonical_asset_id=INITIAL['asset_ids'][0],identity_availability='AVAILABLE',identity=dict(description='Synthetic asset',location_ref='Synthetic location')));return
            if path=='/api/engineering-qa/inspections' and request.method=='GET':
                query=parse_qs(urlparse(request.url).query);offset=int(query.get('offset',['0'])[0]);limit=int(query.get('limit',['25'])[0]);state['list_requests'].append(dict(offset=offset,limit=limit))
                route.fulfill(json=dict(items=state['records'][offset:offset+limit],total=len(state['records']),offset=offset,limit=limit,has_more=offset+limit<len(state['records']),filter_scope='AUTHORIZED_POPULATION',event_time_basis='INSPECTED_AT'));return
            if path=='/api/engineering-qa/inspections' and request.method=='POST':
                body=request.post_data_json;state['posts'].append(body)
                key=body['request_id']
                if key not in state['receipts']:
                    draft=body['draft'];row=dict(**draft,record_id='inspection:SYNTHETIC:'+str(len(state['records'])+1),revision=1,status='DRAFT',created_by=state['who']['subject'],created_at='2026-10-20T00:00:00Z',updated_at='2026-10-20T00:00:00Z',review=None,contributors=[state['who']['subject']],review_started_by=None,field_approval='ENGINEER_FIELDS_PENDING',assessment='NOT_ASSESSED',provenance='NADI_MANUAL_INSPECTION',contract_version='1.4' if draft.get('engineering_analysis') or draft.get('sr_references') else '1.3' if draft.get('work_origin') else '1.2')
                    state['receipts'][key]=row;state['records'].append(row)
                row=state['receipts'][key]
                if state['hold_write']:state['writes'].append((route,row))
                else:route.fulfill(status=201,json=row)
                return
            if path.startswith('/api/engineering-qa/inspections/measurement-history'):
                route.fulfill(json=dict(items=[],total=0,offset=0,limit=25,has_more=False,filter_scope='AUTHORIZED_POPULATION',event_time_basis='MEASURED_AT'));return
            if path.startswith('/api/engineering-qa/inspections/'):
                rid=path.split('/')[4]
                row=next((r for r in state['records'] if r['record_id']==rid),None)
                if path.endswith('/history'):route.fulfill(json=[])
                elif row:route.fulfill(json=row)
                else:route.fulfill(status=404,json={'detail':{'code':'NOT_FOUND'}})
                return
            state['escaped'].append(request.url);route.abort()
        context.route('**/*',respond)
        try:
            page.goto(ORIGIN+'/pdm')
            page.add_style_tag(content='#pdm-fixture-diagnostics { display: none; }')
            page.get_by_role('button',name='Input Pengukuran',exact=True).wait_for()
            test(page,state)
            require(not state['escaped'],'unexpected/external request: '+str(state['escaped']))
            for body in state['posts']:
                require(body['draft'].get('work_origin')==dict(source='DEPARTMENT_REQUEST',requesting_department='Synthetic EPA',reported_asset_label='Synthetic unknown conveyor'),'write/retry lost source context')
                require(body['draft'].get('engineering_analysis')==dict(notes='Synthetic manual engineer reasoning',recommended_follow_up='Synthetic manual follow-up',provenance='HUMAN_ENTERED_ENGINEER_NOTES'),'write/retry lost manual analysis')
                require(body['draft'].get('sr_references')==[dict(sr_number='00012/SYNTHETIC',follow_up_note='Synthetic follow-up, SR unverified',system='MAXIMO',verification='REPORTED_UNVERIFIED')],'write/retry lost unverified SR context')
            results.append(dict(scenario=name,status='PASS',writes=len(state['posts']),navigations=len(state['navigations'])))
            print('PASS',name,flush=True)
        except Exception as error:
            results.append(dict(scenario=name,status='FAIL',error=str(error),trace=traceback.format_exc(),dom=page.evaluate('''()=>{const b=document.body.cloneNode(true);b.querySelector('#pdm-fixture-diagnostics')?.remove();return b.innerText||b.textContent;}''')[:5000],headings=page.locator('h1,h2,[role=status]').all_text_contents(),held_sessions=len(state['sessions']),browser_errors=state['errors'],fetch_debug=page.evaluate('window.fixtureFetchDebug||[]')))
            print('FAIL',name,str(error),flush=True)
        finally:
            context.close()
            args.report.write_text(json.dumps(dict(results=results,scope='actual imported components; synthetic .invalid interception only; no local QA/primary runtime/network'),indent=2)+'\n')

    def diagnostics(page):return json.loads(page.locator('#pdm-fixture-diagnostics').text_content())
    def edit(page):
        page.get_by_role('button',name='Input Pengukuran',exact=True).click()
        page.get_by_label('Jenis formulir',exact=True).select_option('WORKBOOK')
        page.get_by_label('Profil sheet / blok input',exact=True).select_option('wb-fan-s001-b01')
        page.get_by_label('Asal pekerjaan',exact=True).select_option('DEPARTMENT_REQUEST')
        page.get_by_label('Bidang peminta',exact=True).fill('Synthetic EPA')
        page.get_by_label('Label aset pada permintaan / temuan (opsional)',exact=True).fill('Synthetic unknown conveyor')
        page.get_by_label('Catatan analisis engineer (manual)',exact=True).fill('Synthetic manual engineer reasoning')
        page.get_by_label('Saran tindak lanjut engineer (manual, opsional)',exact=True).fill('Synthetic manual follow-up')
        page.get_by_role('button',name='Tambah referensi SR',exact=True).click()
        page.get_by_label('Nomor SR 1',exact=True).fill('00012/SYNTHETIC')
        page.get_by_label('Catatan tindak lanjut SR 1 (opsional)',exact=True).fill('Synthetic follow-up, SR unverified')
        page.get_by_label('Versi metode / prosedur',exact=True).fill('synthetic-auth-focus-marker')
        page.get_by_label('Tipe nilai sumber 1',exact=True).select_option('NUMERIC')
        page.get_by_label('Nilai sumber 1',exact=True).fill('0')
        require(diagnostics(page)['recovery']['entry']['capture']['rows'][0]['value']=='0','draft not cached')
    def focus_hold(page,state):
        state['hold_session']=True
        page.evaluate('window.dispatchEvent(new Event("focus"))')
        # Keep the assertion/release well inside the real wrapper's five-second
        # request deadline. The test diagnostic must not affect page geometry.
        page.wait_for_function("Array.from(document.querySelectorAll('h1')).some(h=>h.textContent==='Memeriksa sesi…')",timeout=2000)
        require(page.evaluate("document.querySelector('form.engineering-form')===null"),'private editor remained mounted during checking')
        require(state['sessions'],'session check not held')
    def same_identity(page,state):
        state['hold_session']=False
        held=state['sessions'][:];state['sessions'].clear()
        for route in held:route.fulfill(json=state['who'])
        page.get_by_role('button',name='Input Pengukuran',exact=True).wait_for()
    def check_recovered(page):
        page.get_by_role('button',name='Input Pengukuran',exact=True).click()
        page.get_by_label('Versi metode / prosedur',exact=True).wait_for()
        require(page.get_by_label('Versi metode / prosedur',exact=True).input_value()=='synthetic-auth-focus-marker','same-identity remount lost version')
        require(page.get_by_label('Nilai sumber 1',exact=True).input_value()=='0','same-identity remount lost zero/source capture')
        require(page.get_by_label('Asal pekerjaan',exact=True).input_value()=='DEPARTMENT_REQUEST','same-identity remount lost work origin')
        require(page.get_by_label('Bidang peminta',exact=True).input_value()=='Synthetic EPA','same-identity remount lost requesting department')
        require(page.get_by_label('Catatan analisis engineer (manual)',exact=True).input_value()=='Synthetic manual engineer reasoning','same identity lost manual analysis')
        require(page.get_by_label('Saran tindak lanjut engineer (manual, opsional)',exact=True).input_value()=='Synthetic manual follow-up','same identity lost follow-up')
        require(page.get_by_label('Nomor SR 1',exact=True).input_value()=='00012/SYNTHETIC','same identity lost SR number')
        require(page.get_by_label('Catatan tindak lanjut SR 1 (opsional)',exact=True).input_value()=='Synthetic follow-up, SR unverified','same identity lost SR note')
        require(page.get_by_label('Label aset pada permintaan / temuan (opsional)',exact=True).input_value()=='Synthetic unknown conveyor','same-identity remount lost reported asset label')
    def focus_draft(page,state):
        edit(page);before=diagnostics(page)['recovery'];focus_hold(page,state)
        require(diagnostics(page)['recovery']==before,'provider draft destroyed during auth checking')
        same_identity(page,state);check_recovered(page)
        require(not state['posts'],'focus caused unsolicited write')
    scenario('same identity focus: AuthenticatedWorkspace hides private view, outer provider retains exact workbook draft, real form recovers',focus_draft)

    def pending(page,state,status):
        edit(page);state['hold_write']=True
        page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
        page.wait_for_function('JSON.parse(document.querySelector("#pdm-fixture-diagnostics").textContent).busy===true')
        require(len(state['posts'])==1,'expected one pending create')
        focus_hold(page,state);require(diagnostics(page)['busy'],'pending provider lock destroyed')
        same_identity(page,state)
        page.get_by_role('button',name='Input Pengukuran',exact=True).click()
        require(page.get_by_role('button',name='Simpan draf inspeksi',exact=True).count()==0,'second create editor opened during pending write')
        route,row=state['writes'].pop()
        state['hold_write']=False
        if status==200:
            route.fulfill(status=201,json=row)
            page.locator('.product-record-detail').wait_for()
            require(page.get_by_role('button',name='Simpan draf inspeksi',exact=True).count()==0,'successful late create left active unsaved editor')
            require(diagnostics(page)['recovery'] is None,'late successful create left stale recovery')
            require(len(state['posts'])==1 and len(state['records'])==1,'late success duplicated record')
            page.locator('.inspection-provenance > summary').click()
            require(row['record_id'] in page.locator('.product-record-detail').inner_text(),'completion navigated wrong record')
        else:
            route.fulfill(status=503,json={'detail':{'code':'QA_BACKEND_UNAVAILABLE'}})
            page.wait_for_function('JSON.parse(document.querySelector("#pdm-fixture-diagnostics").textContent).busy===false')
            check_recovered(page)
            page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
            page.locator('.product-record-detail').wait_for()
            require(len(state['posts'])==2 and state['posts'][0]['request_id']==state['posts'][1]['request_id'],'lost ACK retry changed intent ID')
            require(len(state['records'])==1,'lost ACK remount retry duplicated record')
    scenario('pending create→auth checking→same identity→late200 consumes completion and selects exact persisted record once',lambda p,s:pending(p,s,200))
    scenario('committed create/lost ACK→auth checking→same identity→503→recovered retry reuses exact ID and one record',lambda p,s:pending(p,s,503))

    def other_record(page,state):
        edit(page);original=diagnostics(page)['recovery']
        state['records'].append(dict(record_id='inspection:SYNTHETIC:B',canonical_asset_id=INITIAL['asset_ids'][0],
            method='OTHER',method_version='synthetic-record-B',inspector_ref=INITIAL['subject'],inspected_at=None,
            operating_context=None,measurements=[],observations=[],interpretations=[],attachments=[],case_refs=[],
            method_extension={},revision=1,status='DRAFT',created_by=INITIAL['subject'],
            created_at='2026-10-20T00:00:00Z',updated_at='2026-10-20T00:00:00Z',review=None,
            contributors=[INITIAL['subject']],review_started_by=None,field_approval='ENGINEER_FIELDS_PENDING',
            assessment='NOT_ASSESSED',provenance='NADI_MANUAL_INSPECTION'))
        page.evaluate("fixtureRemountPdm('/pdm?record=inspection%3ASYNTHETIC%3AB')")
        page.get_by_role('button',name='Ubah draf inspeksi',exact=True).wait_for()
        page.once('dialog',lambda d:d.dismiss())
        page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
        require(page.get_by_role('button',name='Simpan revisi draf',exact=True).count()==0,'rejected discard still opened B editor')
        require(diagnostics(page)['recovery']==original,'rejected B edit overwrote private draft A')
        page.evaluate("fixtureRemountPdm('/pdm')")
        page.get_by_role('button',name='Input Pengukuran',exact=True).wait_for();check_recovered(page)
        page.evaluate("fixtureRemountPdm('/pdm?record=inspection%3ASYNTHETIC%3AB')")
        page.get_by_role('button',name='Ubah draf inspeksi',exact=True).wait_for()
        page.once('dialog',lambda d:d.accept())
        page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
        page.get_by_role('button',name='Simpan revisi draf',exact=True).wait_for()
        require(diagnostics(page)['recovery'] is None,'accepted discard retained A')
        require(page.get_by_label('Versi metode / prosedur',exact=True).input_value()=='synthetic-record-B','B edit restored another record')
        page.get_by_role('button',name='Batal input',exact=True).click()
        require(diagnostics(page)['recovery'] is None,'pristine B cancel restored discarded draft')
        require(not state['posts'],'navigation/discard unexpectedly saved data')
    scenario('global draft A→explicit record B: rejected Edit preserves A; resume A exact; accepted discard opens B; pristine cancel does not save',other_record)

    def unavailable_retry(page,state,pending_write=False):
        edit(page);original=diagnostics(page)['recovery']
        if pending_write:
            state['hold_write']=True
            page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
            page.wait_for_function('JSON.parse(document.querySelector("#pdm-fixture-diagnostics").textContent).busy===true')
        focus_hold(page,state);state['hold_session']=False
        for route in state['sessions'][:]:route.fulfill(status=503,json={'detail':{'code':'IDENTITY_STORE_UNAVAILABLE'}})
        state['sessions'].clear()
        page.get_by_role('heading',name='Otoritas sesi tidak tersedia',exact=True).wait_for()
        require(diagnostics(page)['recovery']==original,'unavailable session cleared retained private draft')
        page.get_by_role('button',name='Periksa kembali',exact=True).click()
        page.get_by_role('button',name='Input Pengukuran',exact=True).wait_for()
        require(len(state['navigations'])==1,'transient retry reloaded browser and destroyed workspace provider')
        require(diagnostics(page)['recovery']==original,'retry lost exact private draft')
        if pending_write:
            require(diagnostics(page)['busy'],'retry lost pending command lock')
            route,row=state['writes'].pop();state['hold_write']=False
            route.fulfill(status=503,json={'detail':{'code':'QA_BACKEND_UNAVAILABLE'}})
            page.wait_for_function('JSON.parse(document.querySelector("#pdm-fixture-diagnostics").textContent).busy===false')
            check_recovered(page)
            page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
            page.locator('.product-record-detail').wait_for()
            require(len(state['posts'])==2 and state['posts'][0]['request_id']==state['posts'][1]['request_id'],'transient auth retry lost pending receipt identity')
            require(len(state['records'])==1,'transient auth retry duplicated committed record')
        else:
            check_recovered(page);require(not state['posts'],'session retry unexpectedly wrote draft')
    scenario('transient503 retry: private views stay closed until same identity verified, exact draft retained without full reload',lambda p,s:unavailable_retry(p,s,False))
    scenario('pending lostACK→auth503→retry retains lock/receipt; final503→sameID retry persists one record',lambda p,s:unavailable_retry(p,s,True))

    def bounded_list(page,state):
        for index in range(2):
            if index:
                page.get_by_role('button',name='Kembali ke register',exact=True).click()
            edit(page);page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click();page.locator('.product-record-detail').wait_for()
        page.get_by_role('button',name='Register Inspeksi',exact=True).click()
        require(all(q['limit']==1 for q in state['list_requests']),'inspection list still requests unbounded25 capture records')
        require(page.locator('.pdm-register tbody tr').count()==1,'one-record page rendered wrong record count')
        page.get_by_role('button',name='Halaman berikutnya',exact=True).click()
        page.wait_for_function("document.querySelector('.page-number')?.textContent==='2'")
        require(state['list_requests'][-1]==dict(offset=1,limit=1),'next page not offset1/limit1')
        page.get_by_text('Identitas inspeksi',exact=True).click()
        require('inspection:SYNTHETIC:2' in page.locator('.pdm-register').inner_text(),'next page did not load exact second record')
    scenario('bounded capture listing requests1 and honest server pagination advances offset1 without changing proxy budget',bounded_list)

    def multiline(page,state):
        edit(page)
        page.get_by_label('Tipe nilai sumber 1',exact=True).select_option('TEXT')
        page.get_by_label('Nilai sumber 1',exact=True).fill('Synthetic source line1\nline2')
        page.get_by_label('Tipe Waktu asli / serial',exact=True).first.select_option('TEXT')
        page.get_by_label('Waktu asli / serial',exact=True).first.fill('Synthetic raw clock line1\nline2')
        field=page.locator('.pdm-source-row').first
        field.locator('details > summary').click()
        field.get_by_role('button',name='Tambah konteks field',exact=True).click()
        field.get_by_label('Label konteks',exact=True).fill('Synthetic multiline context')
        field.get_by_label('Tipe Konteks asli',exact=True).select_option('TEXT')
        field.get_by_label('Konteks asli',exact=True).fill('Synthetic metadata line1\nline2')
        page.get_by_role('button',name='Simpan draf inspeksi',exact=True).click()
        page.locator('.product-record-detail').wait_for()
        capture=state['posts'][0]['draft']['input_capture']
        require(capture['rows'][0]['raw_value']=='Synthetic source line1\nline2','source multiline text normalized')
        require(capture['rows'][0]['contexts'][0]['raw_value']=='Synthetic metadata line1\nline2','metadata multiline text normalized')
        require(capture['clocks'][0]['raw_value']=='Synthetic raw clock line1\nline2','clock multiline text normalized')
        page.get_by_role('button',name='Ubah draf inspeksi',exact=True).click()
        require(page.get_by_label('Nilai sumber 1',exact=True).input_value()=='Synthetic source line1\nline2','reopened source multiline differs')
        require(page.get_by_label('Waktu asli / serial',exact=True).first.input_value()=='Synthetic raw clock line1\nline2','reopened clock multiline differs')
    scenario('actual textareas preserve multiline source, metadata and raw-clock strings in POST and reopened editor',multiline)

    def changed(page,state,patch):
        edit(page);focus_hold(page,state)
        state['who']={**state['who'],**patch};state['hold_session']=False
        for route in state['sessions'][:]:route.fulfill(json=state['who'])
        state['sessions'].clear()
        page.wait_for_function('document.querySelector("#pdm-fixture-diagnostics") && JSON.parse(document.querySelector("#pdm-fixture-diagnostics").textContent).recovery===null')
        require(len(state['navigations'])>=2,'identity change did not reload private workspace')
        require(not state['posts'],'identity refresh wrote a draft')
    scenario('changed subject reloads workspace and destroys old private capture recovery',lambda p,s:changed(p,s,dict(subject='local:synthetic-other',username='synthetic-other')))
    scenario('changed role reloads workspace and destroys old private capture recovery',lambda p,s:changed(p,s,dict(roles=['REVIEWER'])))
    scenario('changed asset scope reloads workspace and destroys old private capture recovery',lambda p,s:changed(p,s,dict(asset_ids=['asset:SYNTHETIC:B'])))

    def revoked(page,state,status):
        edit(page);focus_hold(page,state);state['hold_session']=False
        for route in state['sessions'][:]:route.fulfill(status=status,json={'detail':{'code':'IDENTITY_REVOKED'}})
        state['sessions'].clear()
        page.get_by_role('heading',name='Login fixture',exact=True).wait_for()
        require(page.get_by_label('Nilai sumber 1',exact=True).count()==0,'revoked private form remained visible')
        require(page.locator('#pdm-fixture-diagnostics').count()==0,'revoked workspace provider survived full login navigation')
    for status in (401,403):scenario('session'+str(status)+' closes private workspace and navigates login with destroyed capture cache',lambda p,s,status=status:revoked(p,s,status))
    browser.close()
if not results:raise SystemExit('No scenarios selected')
raise SystemExit(1 if any(r['status']!='PASS' for r in results) else 0)

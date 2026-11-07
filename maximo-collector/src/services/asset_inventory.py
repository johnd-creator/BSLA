"""Manual, bounded source inventory; source identities and WO references never change."""
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time
import zipfile
import xml.etree.ElementTree as ET

from sqlalchemy import select
from src.adapters.maximo.mappers import equipment_from_payload
from src.adapters.maximo.oslc_client import ASSET_DETAIL_FIELDS, oslc_timestamp
from src.repositories.models import EquipmentOrm
from src.repositories.asset_inventory import AssetInventoryStore, AssetInventoryOrm
from src.services.sync import SyncStats

CATEGORIES = {'S':'system', 'E':'equipment', 'C':'component', 'P':'part'}
RUN_OBJECT = 'mxapiasset_inventory'


def read_role_reference(path):
    """Read the known engineer workbook, only role and exact KKS columns, never aliases."""
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('workbook exceeds bounded input size')
    ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as book:
        if sum(i.file_size for i in book.infolist()) > 100 * 1024 * 1024:
            raise ValueError('expanded workbook exceeds bounded input size')
        sheets = ET.fromstring(book.read('xl/workbook.xml')).find('s:sheets', ns)
        if sheets is None or len(sheets) != 1 or sheets[0].get('name') != 'HIRARKI REVISI':
            raise ValueError('unexpected engineer reference sheet')
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            strings = [''.join(t.text or '' for t in item.findall('.//s:t', ns))
                       for item in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        rows = ET.fromstring(book.read('xl/worksheets/sheet1.xml')).findall('.//s:row', ns)
        index = defaultdict(list)
        for row in rows:
            values = {}
            for cell in row.findall('s:c', ns):
                col = ''.join(c for c in cell.get('r', '') if c.isalpha())
                if col not in {'A','B','E'}: continue
                item = cell.find('s:v', ns)
                value = item.text if item is not None else ''
                if cell.get('t') == 's' and value: value = strings[int(value)]
                if cell.get('t') == 'inlineStr': value = ''.join(t.text or '' for t in cell.findall('.//s:t', ns))
                values[col] = (value or '').strip()
            if row.get('r') == '1':
                if values.get('B') != 'KKS OLD' or values.get('E') != 'KKS NEW':
                    raise ValueError('unexpected reference headers')
                continue
            role = values.get('A', '').upper()
            for col in ('B','E'):
                identity = values.get(col, '')
                if identity and identity not in {'#N/A', '#REF!', '#VALUE!'}:
                    index[identity].append({'row':int(row.get('r')), 'column':'old_kks' if col == 'B' else 'new_kks', 'role':role})
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'name':path.name, 'index':dict(index)}


def classify(identity, reference):
    evidence = reference['index'].get(identity, [])
    roles = {row['role'] for row in evidence}
    category = CATEGORIES[next(iter(roles))] if len(roles) == 1 and roles <= CATEGORIES.keys() else 'unknown'
    return category, {'basis':'EXACT_SOURCE_ID_WORKBOOK_ROLE', 'status':'INDICATIVE_DOCUMENT_ROLE',
        'sha256':reference['sha256'], 'reference_name':reference['name'], 'rows':evidence,
        'reason':'EXACT_CONSISTENT_ROLE' if category != 'unknown' else ('CONFLICT_OR_UNKNOWN_ROLE' if evidence else 'NO_EXACT_IDENTIFIER')}


def resolve_scope(rows):
    """Seeds are explicit CS01; descend exact source parent links, never infer unit.

    Ancestors supply context only and cannot enroll siblings. Explicit different
    units are a hard boundary in either direction. Cycles terminate by identity.
    """
    valid = {r['assetnum']:r for r in rows if r.get('assetnum') and r.get('siteid') == 'BSR' and r.get('orgid') == 'IP'}
    children = defaultdict(list)
    for identity, row in valid.items():
        children[row.get('parent')].append(identity)
    admitted = {identity:'DIRECT_SOURCE_UNIT' for identity, row in valid.items() if row.get('eq11') == 'CS01'}
    queue = deque(admitted)
    while queue:
        parent = queue.popleft()
        for identity in children[parent]:
            if identity not in admitted and valid[identity].get('eq11') in (None, '', 'CS01'):
                admitted[identity] = 'SOURCE_PARENT_CHAIN'; queue.append(identity)
    # Do not descend from context ancestors, which would admit other plant branches.
    queue = deque(admitted)
    while queue:
        identity = queue.popleft()
        parent = valid[identity].get('parent')
        if parent in valid and parent not in admitted and valid[parent].get('eq11') in (None, '', 'CS01'):
            admitted[parent] = 'SOURCE_ANCESTOR_CONTEXT'; queue.append(parent)
    return admitted


def local_payloads(database):
    from src.services.local_mart_projector import _maximo_source
    with database.session() as session:
        inactive = set(session.scalars(select(AssetInventoryOrm.asset_id).where(AssetInventoryOrm.active.is_(False))))
        rows = session.scalars(select(EquipmentOrm)).all()
        payloads = []
        for row in rows:
            if row.id in inactive: continue
            source = _maximo_source(row)
            # Equipment.unit may historically fall back to plant. Only the
            # explicit quarantined Maximo eq11 field proves a unit seed.
            source["eq11"] = ((row.sources or {}).get("maximo") or {}).get("eq11")
            payloads.append(source)
        return payloads


def refresh_inventory(store, reference, *, client=None, max_requests=50, max_seconds=180, page_size=50, monotonic=time.monotonic):
    if page_size not in (25, 50, 100):
        raise ValueError('manual page size must be 25, 50 or 100 within runtime config')
    if not 1 <= max_requests <= 500 or not 1 <= max_seconds <= 900:
        raise ValueError('manual scan budget must be 1..500 requests and 1..900 seconds')
    inventory = AssetInventoryStore(store._db)
    started = datetime.now(timezone.utc)
    result = {'mode':'LOCAL_ONLY' if client is None else 'MANUAL_SOURCE', 'requests':0, 'source_rows':0,
        'inserted':0, 'updated':0, 'unchanged':0, 'errors':0, 'full_source_baseline_complete':False,
        'stop_reason':'LOCAL_ONLY' if client is None else 'COMPLETE', 'scope':{'site':'BSR','org':'IP','unit':'CS01'}}
    with store.work_order_recovery_lock() as acquired:
        if not acquired: return {**result, 'stop_reason':'SOURCE_BUSY'}
        payloads = {r['assetnum']:r for r in local_payloads(store._db)}
        fresh = {}
        if client is not None:
            before = client.request_telemetry['business_requests']; start = monotonic()
            try:
                with client.bounded_requests(max_requests):
                    pages = iter(client.iterate_pages('mxapiasset', where='siteid="BSR"', required_scope='siteid="BSR"',
                            select=list(ASSET_DETAIL_FIELDS), page_size=page_size, max_pages=max_requests,
                            identity_field='assetnum', strict_members=True, allow_resource_links=False))
                    while True:
                        if monotonic() - start > max_seconds:
                            result['stop_reason'] = 'TIME_BUDGET'; break
                        try: page = next(pages)
                        except StopIteration:
                            result['full_source_baseline_complete'] = True; break
                        # Validate the whole page before admitting it. Different unit is
                        # allowed in scan context only; it is never operationally persisted.
                        page_ids = set()
                        for raw in page:
                            identity = raw.get('assetnum')
                            if not isinstance(identity, str) or not identity.strip() or identity != identity.strip() or len(identity)>60:
                                raise ValueError('invalid source identity')
                            if raw.get('siteid') != 'BSR' or raw.get('orgid') != 'IP':
                                raise ValueError('source scope mismatch')
                            if identity in fresh or identity in page_ids: raise ValueError('duplicate source identity')
                            page_ids.add(identity)
                            equipment_from_payload(raw)
                        for raw in page: fresh[raw['assetnum']] = dict(raw)
            except Exception as error:
                result['errors'] = 1; result['stop_reason'] = type(error).__name__
            result['requests'] = client.request_telemetry['business_requests'] - before
            result['source_rows'] = len(fresh)
            for identity, incoming in fresh.items():
                old = oslc_timestamp(payloads.get(identity, {}).get("changedate"))
                new = oslc_timestamp(incoming.get("changedate"))
                if old and old.tzinfo is None: old = old.replace(tzinfo=timezone.utc)
                if new and new.tzinfo is None: new = new.replace(tzinfo=timezone.utc)
                if old is None or (new is not None and new >= old):
                    payloads[identity] = incoming
        admitted = resolve_scope(payloads.values())
        for identity, basis in sorted(admitted.items()):
            if identity in fresh:
                outcome = store.upsert_equipment_manual(equipment_from_payload(fresh[identity]), raw=fresh[identity])
                result[outcome] += 1
            category, proof = classify(identity, reference)
            inventory.upsert(identity, category, basis, proof, started, seen_in_source=identity in fresh)
        inventory.deactivate_outside(admitted)
        result['inventory_assets'] = len(admitted)
        result['category_counts'] = dict(Counter(classify(identity, reference)[0] for identity in admitted))
        result['retained_not_seen_in_scan'] = len(set(admitted)-set(fresh)) if client is not None else len(admitted)
        inventory.record_scan(result, started)
        if client is not None:
            stats = SyncStats(RUN_OBJECT, mode='manual_full' if result['full_source_baseline_complete'] else 'manual_partial', started_at=started)
            stats.rows_seen=result['source_rows'];stats.upserted=result['inserted']+result['updated'];stats.errors=result['errors']
            stats.finished_at=datetime.now(timezone.utc);store.record_run(stats)
    return result

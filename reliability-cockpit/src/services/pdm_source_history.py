"""Read-only provisional source history under existing AUTHOR ownership and asset authority.

No source writer, schema preparation, grant, diagnosis or canonical trend path.
Every proof lookup is preceded by an authorized event in the same owning store.
"""
from hashlib import sha256
import json, re, copy
from sqlalchemy import select, func, or_, inspect
from src.domain.engineering import Role, EngineeringError
from src.repositories.pdm_source_history import Source, Profile, Cell, Event, Alias, Batch, TABLES
from src.repositories.human_records import RevisionRow
from src.services.pdm_source_interpretation import requested_cells, interpret, rule


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value): return sha256(canonical(value).encode()).hexdigest()


RESPONSE_BYTES = 900*1024  # Below the unchanged 2 MiB browser/proxy cap.


def bounded_page(base, summaries, limit):
    items = []
    for item in summaries[:limit]:
        candidate = dict(base, items=items+[item], next_after=item.get('event_key',item.get('batch_id')),has_more=True)
        if len(canonical(candidate).encode()) > RESPONSE_BYTES: break
        items.append(item)
    if summaries and not items: raise EngineeringError('HISTORY_RESPONSE_BOUND',413)
    more = len(summaries)>len(items)
    return dict(base,items=items,has_more=more,next_after=(items[-1].get('event_key',items[-1].get('batch_id')) if more else None))



class SourceHistoryService:
    def __init__(self, inspections, *, enabled=False):
        self.inspections, self.engine, self.enabled = inspections, inspections.repo.engine, enabled

    def ready(self):
        with self.engine.connect() as c:
            return set(TABLES) <= set(inspect(c).get_table_names())

    def scope(self, actor):
        self.inspections.gate(actor)
        if not self.enabled: raise EngineeringError('FEATURE_DISABLED', 404)
        if not self.ready(): raise EngineeringError('HISTORY_SCHEMA_PREREQUISITE', 503)
        # Full RAW source may include unclassified context: never infer reviewer/admin access.
        if Role.AUTHOR not in actor.roles: raise EngineeringError('HISTORY_AUTHOR_SCOPE_REQUIRED',403)
        return [Event.c.access_asset_id.in_(actor.asset_ids),Event.c.owner_id==actor.principal_id]

    @staticmethod
    def page(limit, after):
        if type(limit) is not int or not 1 <= limit <= 100 or after and not re.fullmatch('[0-9a-f]{64}', after):
            raise EngineeringError('INVALID_PAGINATION', 422)

    def listing(self, actor, *, limit=25, after='', source_ref=None, sheet_index=None, classification=None, kind=None):
        self.page(limit, after); where = self.scope(actor)
        for column, value, maximum in [(Event.c.source_ref, source_ref, 80), (Event.c.classification, classification, 40), (Event.c.kind, kind, 40)]:
            if value is not None:
                if not isinstance(value, str) or len(value) > maximum: raise EngineeringError('INVALID_FILTER', 422)
                where.append(column == value)
        if sheet_index is not None:
            if type(sheet_index) is not int or not 0 <= sheet_index < 10000: raise EngineeringError('INVALID_FILTER', 422)
            where.append(Event.c.sheet_index == sheet_index)
        with self.engine.connect() as c:
            total = c.scalar(select(func.count()).select_from(Event).where(*where))
            if after: where.append(Event.c.event_key > after)
            rows = c.execute(select(Event, Source.c.document.label('source_document')).join(Source).where(*where).order_by(Event.c.event_key).limit(limit+1)).mappings().all()
        return bounded_page({'scope':'AUTHORIZED_PROVISIONAL_SOURCE','total':total,'limit':limit,
                             'canonical_eligible':False,'time_basis':'SOURCE_CLAIMS_NOT_ENTRY_TIME'},
                            [self.summary(row) for row in rows], limit)

    @staticmethod
    def summary(row):
        source = row['source_document']; document = row['document']
        sheet = source['sheets'][row['sheet_index']]
        clocks = copy.deepcopy(document['clocks']); omitted = False
        for clock in clocks:
            for key in ('raw_value','raw_values'):
                if key in clock and len(canonical(clock[key]).encode())>256:
                    clock[key] = None; omitted = True
        return {k: row[k] for k in ('event_key', 'source_ref', 'sheet_index', 'profile_id', 'axis', 'position', 'kind', 'classification')} | {
            'source_sha256': row['source_sha'], 'sheet_label': sheet['label'], 'source_asset_label': document['source_asset_label'],
            'mapping': document['mapping'], 'reasons': document['reasons'], 'clocks': clocks, 'raw_clock_values_in_detail': omitted,
            'field_claims': len(document['fields']), 'distinct_source_cells': len({f['cell'] for f in document['fields']}),
            'provenance': 'PROVISIONAL_HISTORICAL_SOURCE', 'approval': 'NOT_REVIEWED', 'canonical_eligible': False}

    def detail(self, actor, event_key, *, offset=0, limit=25):
        self.page(limit, event_key)
        if type(offset) is not int or not 0 <= offset <= 10000: raise EngineeringError('INVALID_PAGINATION', 422)
        scope = self.scope(actor)
        with self.engine.connect() as c:
            row = c.execute(select(Event, Source.c.document.label('source_document')).join(Source).where(*scope, Event.c.event_key == event_key)).mappings().first()
            if not row: raise EngineeringError('NOT_FOUND', 404)
            profile = c.scalar(select(Profile.c.document).where(Profile.c.profile_hash == row['profile_hash']))
            meta = {field['id']: field for field in profile['fields']}
            refs = row['document']['fields']; chosen = refs[offset:offset+limit]
            addresses = set(row['document']['clock_cells'])
            addresses.update(requested_cells(row))
            for ref in chosen:
                addresses.add(ref['cell']); field = meta.get(ref['field_id'], {})
                addresses.update(field.get('header_cells', [])); addresses.update(field.get('unit_cells', []))
            anchors = []
            if rule(row) == 'BC43' and row['position'] == 23 and any(f['cell'] == 'L23' for f in chosen):
                anchors = c.execute(select(Event).where(*scope, Event.c.source_sha == row['source_sha'],
                    Event.c.sheet_index == row['sheet_index'], Event.c.profile_hash == row['profile_hash'],
                    Event.c.profile_id == row['profile_id'], Event.c.axis == 'ROW', Event.c.position.in_([22, 24])).limit(3)).mappings().all()
                # Neighbor values need their own authorized event, not just shared source bytes.
                if len(anchors) == 2 and {a['position'] for a in anchors} == {22, 24}:
                    addresses.update({'A22', 'L22', 'A24', 'L24'})
            cells = {r['coordinate']: r['document'] for r in c.execute(select(Cell).where(Cell.c.source_sha == row['source_sha'], Cell.c.sheet_index == row['sheet_index'], Cell.c.coordinate.in_(addresses))).mappings()}
            def proof(address): return {'coordinate': address, **cells.get(address, {'raw_value': None, 'presence': 'NO_POPULATED_CELL_IN_COMPLETE_SOURCE_CENSUS'})}
            fields = []
            for ref in chosen:
                field = meta.get(ref['field_id'], {})
                fields.append({**ref, 'label_claim': field.get('source_label'), 'unit_claim': field.get('unit'),
                               'source_point_claim': field.get('source_point'), 'source_axis_claim': field.get('source_axis'),
                               'value': proof(ref['cell']), 'headers': [proof(a) for a in field.get('header_cells', [])],
                               'unit_evidence': [proof(a) for a in field.get('unit_cells', [])],
                               'interpretation': 'SOURCE_CLAIMS_NOT_CANONICAL_QUALIFICATION'})
            aliases = []
            for link in c.execute(select(Alias).where(Alias.c.event_key == event_key)).mappings():
                try:
                    current = self.inspections.visible(actor, self.inspections.repo.get(c, 'INSPECTION', link['record_id']))
                except EngineeringError: continue
                snapshot = c.scalar(select(RevisionRow.snapshot).where(RevisionRow.kind == 'INSPECTION', RevisionRow.record_id == link['record_id'], RevisionRow.revision == link['revision']))
                if not snapshot or digest(snapshot.get('input_capture')) != link['capture_hash']:
                    raise EngineeringError('HISTORY_ALIAS_PROOF_CHANGED', 409)
                aliases.append({'record_id': current.record_id, 'source_revision': link['revision'], 'current_revision': current.revision, 'relation': link['relation']})
            result = {'item': self.summary(row), 'fields': fields, 'field_total': len(refs), 'offset': offset, 'limit': len(fields) or limit,
                      'has_more': offset+len(fields) < len(refs), 'clock_evidence': [proof(a) for a in row['document']['clock_cells']],
                      'aliases': aliases, 'profile_version': profile['version'], 'classification_hash': row['classification_hash'],
                      'editable': False, 'canonical_eligible': False}
            result['derived_interpretation'] = interpret(row, fields, cells, anchors)
            while len(canonical(result).encode()) > RESPONSE_BYTES and len(fields)>1:
                fields.pop(); result['limit']=len(fields); result['has_more']=offset+len(fields)<len(refs)
                result['derived_interpretation'] = interpret(row, fields, cells, anchors)
            if len(canonical(result).encode()) > RESPONSE_BYTES: raise EngineeringError('HISTORY_RESPONSE_BOUND', 413)
            result['next_offset']=offset+len(fields) if result['has_more'] else None
            result['previous_offset']=max(0,offset-limit) if offset else None
            return result

    def batches(self, actor, *, limit=10, after=''):
        self.page(limit,after); self.scope(actor)
        where = [Batch.c.access_asset_id.in_(actor.asset_ids),Batch.c.owner_id==actor.principal_id]
        if after: where.append(Batch.c.batch_id>after)
        with self.engine.connect() as c:
            rows = c.execute(select(Batch).where(*where).order_by(Batch.c.batch_id).limit(limit+1)).mappings().all()
        return bounded_page({'scope':'AUTHORIZED_PROVISIONAL_SOURCE','limit':limit}, [
            {'batch_id': r['batch_id'], 'state': r['state'], 'cursor': r['cursor'], 'counts': r['manifest']['counts'],
             'coverage': r['manifest']['coverage'], 'canonical_eligible': False} for r in rows],limit)

"""Explicit, resumable CLOSE actual-date recovery for a sealed local cohort.

Not imported by routine sync. No cursor, schedule, core WO column, Mart schema,
Registry, or production business writes. Run the module manually in the existing
Collector runtime. Historical scope uses source reportdate, never the WO number.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo
import re

from sqlalchemy import select
from src.adapters.maximo.actual_dates import clock, evidence, merge_evidence, version
from src.repositories.models import WorkOrderOrm

FIELDS = ('wonum', 'assetnum', 'siteid', 'orgid', 'status', 'reportdate',
          'changedate', 'statusdate', 'actstart', 'actfinish', 'istask')
FLOOR = datetime.fromisoformat('2021-01-01T00:00:00+07:00')
FORMAT = 'bsr-close-actual-backfill/1'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def serialize(value):
    if isinstance(value, datetime):
        return version(value).isoformat()
    raise TypeError('unsupported evidence value')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     default=serialize).encode()).hexdigest()


def save_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as handle:
        json.dump(value, handle, default=serialize, sort_keys=True)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    tmp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def row_identity(row):
    return {'id': row.id, 'equipment_id': row.equipment_id, 'status': row.status,
            'reported_at': serialize(row.reported_at) if row.reported_at else None,
            'source_changed_at': serialize(row.source_changed_at) if row.source_changed_at else None}


def pure_recovery(row, raw, *, observed_at, run_id, ceiling, allow_unknown_reportdate=False):
    """Return dates-only sources and classification; never change valid clocks."""
    sources = deepcopy(row.sources or {})
    previous = sources.get('maximo') or {}
    if not row.id.startswith('BSR') or row.status != 'CLOSE':
        return None, 'LOCAL_NOT_ELIGIBLE'
    if raw.get('wonum') != row.id or raw.get('siteid') != 'BSR' or raw.get('orgid') != 'IP':
        raise ValueError('SOURCE_IDENTITY_OR_SCOPE_MISMATCH')
    if raw.get('status') != 'CLOSE':
        return None, 'SOURCE_NOT_CLOSE'
    if any(previous.get(k) not in (None, expected) for k, expected in (('siteid', 'BSR'), ('orgid', 'IP'))):
        return None, 'LOCAL_SCOPE_CONFLICT'
    if (raw.get('assetnum') or None) != (row.equipment_id or None):
        return None, 'ASSET_IDENTITY_CHANGED_OR_MISSING'
    reported = clock(raw.get('reportdate'), present='reportdate' in raw)
    # Explicit, sealed exact-ID exception only. It establishes actual activity
    # within the requested period, NEVER a guessed report/creation date.
    actuals = [clock(raw.get(f), present=f in raw) for f in ('actstart', 'actfinish')]
    clock_period_exception = (
        allow_unknown_reportdate and row.reported_at is None
        and reported['state'] in ('MISSING', 'UNAVAILABLE')
        and all(c['state'] == 'VALID' for c in actuals)
        and FLOOR <= version(actuals[0]['normalized']) <= version(actuals[1]['normalized']) <= version(ceiling))
    if reported['state'] != 'VALID' and not clock_period_exception:
        return None, 'SOURCE_REPORTDATE_UNKNOWN'
    if not clock_period_exception:
        when = version(raw.get('reportdate'))
        if when < FLOOR or when > version(ceiling):
            return None, 'SOURCE_OUTSIDE_COHORT_DATES'
        if when != version(row.reported_at):
            return None, 'SOURCE_REPORTDATE_CHANGED'
    changed = clock(raw.get('changedate'), present='changedate' in raw)
    if changed['state'] != 'VALID' or version(raw.get('changedate')) != version(row.source_changed_at):
        return None, 'SOURCE_VERSION_CHANGED_OR_UNKNOWN'
    incoming = evidence(raw)
    prior = previous.get('actual_dates')
    if prior:
        valid_old = any(v.get('state') == 'VALID' for v in prior.get('fields', {}).values())
        if valid_old and prior.get('identity') != incoming['identity']:
            return None, 'RETAINED_CLOCK_IDENTITY_CONFLICT'
        for field in ('actstart', 'actfinish'):
            old = prior.get('fields', {}).get(field, {})
            new = incoming['fields'][field]
            if old.get('state') == 'VALID':
                # Do not replace either a valid value or its original provenance.
                checked = clock(old.get('original'))
                if (checked['state'] != 'VALID' or checked['normalized'] != old.get('normalized')
                        or version(old.get('source_changed_at')) is None
                        or version(old.get('source_changed_at')) > version(row.source_changed_at)):
                    return None, 'RETAINED_CLOCK_PROOF_INVALID'
                if new['state'] == 'VALID' and version(old.get('normalized')) != version(new['normalized']):
                    return None, 'RETAINED_VALID_CLOCK_CONFLICT'
                incoming['fields'][field] = deepcopy(old)
    merged = merge_evidence(prior, incoming)
    previous.update(siteid='BSR', orgid='IP', actual_dates=merged,
                    collector_updated_at=observed_at,
                    actual_backfill={'format': FORMAT, 'run_id': run_id,
                                     'observed_at': observed_at,
                                     'source_version': raw['changedate'],
                                     'asset_identity_state': 'EXACT_MATCH' if row.equipment_id else 'UNASSIGNED_OR_UNAVAILABLE',
                                     'observation_states': {k: clock(raw.get(k), present=k in raw)['state']
                                                            for k in ('actstart', 'actfinish')}})
    if clock_period_exception:
        previous['actual_backfill']['scope_basis'] = 'EXACT_ID_SOURCE_ACTUAL_INTERVAL_REPORTDATE_UNKNOWN'
        previous['actual_backfill']['reportdate_state'] = reported['state']
    sources['maximo'] = previous
    states = [merged['fields'][f]['state'] for f in ('actstart', 'actfinish')]
    if states == ['VALID', 'VALID']:
        result = ('PAIR_ALREADY_RETAINED' if prior and all(prior.get('fields', {}).get(f, {}).get('state') == 'VALID' for f in ('actstart', 'actfinish')) else 'PAIR_RECOVERED') if version(merged['fields']['actfinish']['normalized']) >= version(merged['fields']['actstart']['normalized']) else 'REVERSED_CLOCK_PAIR'
    elif 'VALID' in states:
        result = 'ONE_VALID_CLOCK'
    elif 'MISSING' in states:
        result = 'SOURCE_EXPLICIT_MISSING'
    elif 'UNAVAILABLE' in states:
        result = 'SOURCE_FIELDS_OMITTED'
    else:
        result = 'SOURCE_CLOCKS_INVALID_OR_UNZONED'
    return sources, result


def load_plan(directory):
    plan = json.loads((directory / 'cohort.json').read_text())
    seal = plan.pop('sha256')
    if plan.get('format') != FORMAT or digest(plan) != seal:
        raise ValueError('COHORT_SEAL_MISMATCH')
    plan['sha256'] = seal
    identities = [x['id'] for x in plan['cohort']]
    if len(set(identities)) != len(identities) or not identities:
        raise ValueError('INVALID_COHORT')
    if any(not re.fullmatch(r'BSR[A-Za-z0-9_./ -]+', x) for x in identities):
        raise ValueError('INVALID_COHORT_IDENTITIES')
    exceptions = set(plan.get('reportdate_unknown_exceptions') or [])
    if not exceptions.issubset({r['id'] for r in plan['cohort'] if r['reported_at'] is None}):
        raise ValueError('UNKNOWN_REPORTDATE_EXCEPTION_OUTSIDE_COHORT')
    return plan


def create_plan(db, directory):
    if (directory / 'cohort.json').exists():
        raise ValueError('COHORT_ALREADY_EXISTS')
    ceiling = stamp()
    with db.session() as session:
        rows = session.scalars(select(WorkOrderOrm).where(
            WorkOrderOrm.id.startswith('BSR'), WorkOrderOrm.status == 'CLOSE',
            WorkOrderOrm.reported_at >= FLOOR, WorkOrderOrm.reported_at <= version(ceiling)
        ).order_by(WorkOrderOrm.reported_at, WorkOrderOrm.id)).all()
        cohort = [row_identity(row) for row in rows]
    # Give both oldest requested year and current-year examples an early check.
    pilots = [r for r in cohort if r['id'] in {'BSR21/10001', 'BSR21/10002', 'BSR26/10001', 'BSR26/10002', 'BSR26/10003'}]
    pilot_ids = {r['id'] for r in pilots}
    cohort = pilots + [r for r in cohort if r['id'] not in pilot_ids]
    plan = {'format': FORMAT, 'created_at': ceiling, 'floor': FLOOR.isoformat(),
            'ceiling': ceiling, 'scope': {'site': 'BSR', 'organization': 'IP'},
            'cohort': cohort, 'source_total_verified': False}
    plan['sha256'] = digest(plan)
    save_json(directory / 'cohort.json', plan)
    return {'status': 'PLANNED', 'cohort_size': len(cohort), 'sha256': plan['sha256']}


def reconcile_journals(db, directory, plan=None):
    done, counts = set(), Counter()
    for path in sorted(directory.glob('batch-*.json')):
        doc = json.loads(path.read_text())
        if plan is not None and (doc.get('format') != FORMAT or doc.get('cohort_sha256') != plan['sha256']
                or not {r['id'] for r in doc['outcomes']}.issubset({r['id'] for r in plan['cohort']})):
            raise ValueError('JOURNAL_COHORT_MISMATCH')
        if doc['state'] == 'PREPARED':
            matches_after, matches_before = [], []
            with db.session() as session:
                for item in doc['changes']:
                    row = session.get(WorkOrderOrm, item['id'])
                    if row is None or row_identity(row) != item['identity']:
                        raise ValueError('UNCERTAIN_BATCH_CONCURRENT_CORE_CHANGE')
                    matches_after.append(row.sources == item['after'])
                    matches_before.append(row.sources == item['before'])
            if all(matches_after):
                doc['state'] = 'COMMITTED'; save_json(path, doc)
            elif all(matches_before):
                # DB transaction did not commit. Keep durable backup and allow
                # an explicit later run to fetch current evidence for these IDs.
                doc['state'] = 'ROLLED_BACK_BEFORE_COMMIT'; save_json(path, doc)
            else:
                raise ValueError('UNCERTAIN_BATCH_CONCURRENT_SOURCE_CHANGE')
        if doc['state'] == 'COMMITTED':
            ids = {r['id'] for r in doc['outcomes']}
            if done & ids:
                raise ValueError('DUPLICATE_COMMITTED_COHORT_ID')
            done.update(ids); counts.update(r['result'] for r in doc['outcomes'])
    return done, counts


def apply_batch(db, raw_rows, selected, directory, batch_number, plan):
    expected = {x['id']: x for x in selected}
    raw_by_id = {}
    for raw in raw_rows:
        identity = raw.get('wonum')
        if (identity not in expected or identity in raw_by_id or raw.get('siteid') != 'BSR'
                or raw.get('orgid') != 'IP'):
            raise ValueError('SOURCE_BATCH_IDENTITY_OR_SCOPE_MISMATCH')
        raw_by_id[identity] = raw
    doc = {'format': FORMAT, 'cohort_sha256': plan['sha256'], 'state': 'PREPARED',
           'observed_at': stamp(), 'changes': [], 'outcomes': []}
    path = directory / f'batch-{batch_number:06d}.json'
    if path.exists():
        raise ValueError('BATCH_JOURNAL_ALREADY_EXISTS')
    with db.session() as session:
        for identity in sorted(expected):
            row = session.get(WorkOrderOrm, identity, with_for_update=True)
            new = None
            if row is None or row_identity(row) != expected[identity]:
                result = 'LOCAL_CHANGED_SINCE_PLAN'
            elif identity not in raw_by_id:
                result = 'SOURCE_RECORD_NOT_RETURNED'
            else:
                new, result = pure_recovery(row, raw_by_id[identity], observed_at=doc['observed_at'],
                                            run_id=plan['sha256'], ceiling=plan['ceiling'],
                                            allow_unknown_reportdate=identity in plan.get('reportdate_unknown_exceptions', []))
            doc['outcomes'].append({'id': identity, 'result': result})
            if new is not None:
                doc['changes'].append({'id': identity, 'identity': row_identity(row),
                                       'before': deepcopy(row.sources), 'after': deepcopy(new)})
                row.sources = new
        save_json(path, doc)  # fsync backup/checkpoint BEFORE DB commit
        session.commit()
    doc['state'] = 'COMMITTED'; save_json(path, doc)
    return doc


def prioritize_pending(pending, ceiling):
    """Process the current report year early; preserve the sealed cohort set.

    After the oldest-year pilot, current-year clocks are useful on the default
    UI list while older historical years continue in ascending order.
    """
    zone = ZoneInfo('Asia/Jakarta')
    year = version(ceiling).astimezone(zone).year
    def key(row):
        reported = version(row['reported_at'])
        return (reported is None or reported.astimezone(zone).year != year,
                reported or datetime.max.replace(tzinfo=timezone.utc), row['id'])
    return sorted(pending, key=key)


def run(db, directory, *, batch_size=100, max_batches=20):
    from src.config import MaximoConfig
    from src.repositories.store import CollectorStore
    from src.adapters.maximo.auth import MaximoAuth
    from src.adapters.maximo.oslc_client import OslcClient
    if not 1 <= batch_size <= 100 or not 1 <= max_batches <= 100:
        raise ValueError('BATCH_OR_RUN_LIMIT_EXCEEDED')
    plan = load_plan(directory)
    config = MaximoConfig.from_environment()
    if any(not r['id'].startswith(config.wo_prefixes) for r in plan['cohort']):
        raise ValueError('COHORT_OUTSIDE_CONFIGURED_PREFIXES')
    store = CollectorStore(db)
    # Same lock as scheduled WO sync. No overlapping production requests.
    with store.work_order_recovery_lock() as acquired:
        if not acquired:
            return {'status': 'SOURCE_BUSY', 'writes': 0}
        done, counts = reconcile_journals(db, directory, plan)
        pending = prioritize_pending([r for r in plan['cohort'] if r['id'] not in done], plan['ceiling'])
        client = OslcClient(config, MaximoAuth(config), request_budget=min(400, max_batches * 2))
        cursor_before = store.get_cursor('mxwodetail')
        next_batch = 1 + max([int(p.stem.split('-')[1]) for p in directory.glob('batch-*.json')] or [0])
        processed = 0
        for offset in range(0, min(len(pending), batch_size * max_batches), batch_size):
            selected = pending[offset:offset + batch_size]
            values = ','.join('"' + r['id'] + '"' for r in selected)
            rows = list(client.iterate('mxwodetail', where=f'siteid="BSR" and wonum in [{values}]',
                                      required_scope='siteid="BSR"', select=list(FIELDS),
                                      page_size=batch_size, max_pages=2, identity_field='wonum', strict_members=True))
            doc = apply_batch(db, rows, selected, directory, next_batch, plan)
            next_batch += 1
            processed += len(selected)
            done.update(r['id'] for r in selected)
            counts.update(r['result'] for r in doc['outcomes'])
            status = {'status': 'COMPLETE_LOCAL_COHORT' if len(done) == len(plan['cohort']) else 'PARTIAL_CHECKPOINT',
                      'cohort_size': len(plan['cohort']), 'processed_total': len(done),
                      'remaining': len(plan['cohort']) - len(done), 'processed_this_run': processed,
                      'results': dict(counts), 'requests_this_run': client.request_telemetry,
                      'updated_at': stamp(), 'source_total_verified': False,
                      'routine_cursor_unchanged': store.get_cursor('mxwodetail') == cursor_before}
            if not status['routine_cursor_unchanged']:
                raise ValueError('SOURCE_CURSOR_CHANGED_WHILE_LOCKED')
            save_json(directory / 'progress.json', status)
            print(json.dumps(status), flush=True)
        if not pending:
            return {'status': 'COMPLETE_LOCAL_COHORT', 'cohort_size': len(done), 'results': dict(counts)}
        return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('plan', 'run'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--max-batches', type=int, default=20)
    args = parser.parse_args()
    from src.config import load_env
    from src.repositories.database import get_database
    load_env()
    logging.basicConfig(level=logging.ERROR)
    directory = Path(args.directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        result = create_plan(get_database(), directory) if args.mode == 'plan' else run(
            get_database(), directory, batch_size=args.batch_size, max_batches=args.max_batches)
        print(json.dumps(result), flush=True)
    except Exception as error:
        # No URLs, credentials, response body or DB parameters in public logs.
        print(json.dumps({'status': 'STOPPED', 'error_class': type(error).__name__,
                          'error_code': str(error) if isinstance(error, ValueError) and re.fullmatch('[A-Z_]+', str(error)) else 'DETAILS_REDACTED',
                          'time': stamp()}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()

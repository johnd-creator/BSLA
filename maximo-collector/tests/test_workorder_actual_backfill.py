"""Hermetic recovery tests; no source/operational DB access."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.adapters.maximo.actual_dates import evidence
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import WorkOrderOrm, SyncCursorOrm, EquipmentOrm
from src.repositories.mart_models import MaintenanceEventMartOrm
from src.services.workorder_actual_backfill import FLOOR,pure_recovery,create_plan,load_plan,apply_batch,reconcile_journals,run,prioritize_pending,digest
from src.services.local_mart_projector import CollectorMartProjector
NOW='2026-11-06T00:00:00+00:00'
CHANGE='2021-01-10T09:03:18+00:00'
REPORT='2021-01-01T08:03:48+00:00'
def raw(**kwargs):
    return dict({'wonum':'BSR21/10001','assetnum':'ASSET-1','siteid':'BSR','orgid':'IP','status':'CLOSE','reportdate':REPORT,'changedate':CHANGE,'actstart':'2021-01-04T08:00:00+07:00','actfinish':'2021-01-04T10:30:00+07:00','istask':False},**kwargs)
def make_row(**kwargs):
    return WorkOrderOrm(**dict({'id':'BSR21/10001','equipment_id':'ASSET-1','status':'CLOSE','reported_at':datetime.fromisoformat(REPORT),'source_changed_at':datetime.fromisoformat(CHANGE),'description':'Retained description','is_task':False,'sources':{'maximo':{'extra':{'retained':'unchanged'}}}},**kwargs))
class PureTests(unittest.TestCase):
    def recover(self,row=None,payload=None):return pure_recovery(row or make_row(),payload or raw(),observed_at=NOW,run_id='test',ceiling=NOW)
    def test_old_close_and_metadata_preservation(self):
        row=make_row();before=deepcopy(row.sources);result,state=self.recover(row)
        self.assertEqual(state,'PAIR_RECOVERED');self.assertEqual(row.sources,before)
        self.assertEqual(result['maximo']['extra'],before['maximo']['extra'])
        self.assertEqual(result['maximo']['actual_dates']['fields']['actstart']['state'],'VALID')
        self.assertEqual(row.description,'Retained description')
    def test_source_scope_identity_fail(self):
        for changes in ({'siteid':'OTHER'},{'orgid':'OTHER'},{'wonum':'OTHER'}):
            with self.assertRaises(ValueError):self.recover(payload=raw(**changes))
    def test_status_asset_version_changes_skip(self):
        for changes,state in [({'status':'APPR'},'SOURCE_NOT_CLOSE'),({'assetnum':'OTHER'},'ASSET_IDENTITY_CHANGED_OR_MISSING'),({'changedate':'2021-01-11T00:00:00Z'},'SOURCE_VERSION_CHANGED_OR_UNKNOWN'),({'changedate':None},'SOURCE_VERSION_CHANGED_OR_UNKNOWN')]:
            self.assertEqual(self.recover(payload=raw(**changes)),(None,state))
    def test_reportdate_guards(self):
        for value,state in [(None,'SOURCE_REPORTDATE_UNKNOWN'),('2021-01-01T00:00:00','SOURCE_REPORTDATE_UNKNOWN'),('2020-12-31T23:59:59+07:00','SOURCE_OUTSIDE_COHORT_DATES'),('2027-01-01T00:00:00Z','SOURCE_OUTSIDE_COHORT_DATES')]:
            self.assertEqual(self.recover(payload=raw(reportdate=value)),(None,state))
    def test_inclusive_floor(self):self.assertEqual(self.recover(make_row(reported_at=FLOOR),raw(reportdate=FLOOR.isoformat()))[1],'PAIR_RECOVERED')
    def test_null_and_omitted_distinct(self):
        self.assertEqual(self.recover(payload=raw(actstart=None,actfinish=None))[1],'SOURCE_EXPLICIT_MISSING')
        value=raw();value.pop('actstart');value.pop('actfinish')
        self.assertEqual(self.recover(payload=value)[1],'SOURCE_FIELDS_OMITTED')
    def test_bad_clock_states(self):
        for start,finish,state in [('bad','bad','SOURCE_CLOCKS_INVALID_OR_UNZONED'),('2021-01-01T00:00:00','2021-01-01T01:00:00','SOURCE_CLOCKS_INVALID_OR_UNZONED'),('2021-01-02T00:00:00Z','2021-01-01T00:00:00Z','REVERSED_CLOCK_PAIR')]:
            self.assertEqual(self.recover(payload=raw(actstart=start,actfinish=finish))[1],state)
    def test_preserve_valid_original_and_prevent_replacement(self):
        prior=evidence(raw(changedate='2021-01-09T00:00:00Z'));row=make_row(sources={'maximo':{'actual_dates':prior}})
        result,state=self.recover(row,raw(actstart=None))
        self.assertEqual(result['maximo']['actual_dates']['fields']['actstart'],prior['fields']['actstart'])
        self.assertEqual(self.recover(row,raw(actstart='2021-01-04T09:00:00+07:00')),(None,'RETAINED_VALID_CLOCK_CONFLICT'))
    def test_assetless_clocks_retained_without_invented_asset(self):
        result,state=self.recover(make_row(equipment_id=None),raw(assetnum=None))
        self.assertEqual(state,'PAIR_RECOVERED');self.assertIsNone(result['maximo']['actual_dates']['identity']['assetnum'])
        self.assertEqual(result['maximo']['actual_backfill']['asset_identity_state'],'UNASSIGNED_OR_UNAVAILABLE')
    def test_prioritization_preserves_members_and_uses_wib_report_year(self):
        rows=[{'id':'BSR26/WRONG','reported_at':'2022-01-01T00:00:00Z'},
              {'id':'BSR25/BOUNDARY','reported_at':'2025-12-31T17:00:00Z'},
              {'id':'BSR21/OLD','reported_at':REPORT}]
        ordered=prioritize_pending(rows,NOW)
        self.assertEqual([r['id'] for r in ordered],['BSR25/BOUNDARY','BSR21/OLD','BSR26/WRONG'])
        self.assertEqual({r['id'] for r in rows},{r['id'] for r in ordered})
    def test_unknown_reportdate_requires_explicit_exact_id_exception(self):
        row=make_row(reported_at=None);payload=raw(reportdate=None)
        self.assertEqual(self.recover(row,payload),(None,'SOURCE_REPORTDATE_UNKNOWN'))
        result,state=pure_recovery(row,payload,observed_at=NOW,run_id='test',ceiling=NOW,allow_unknown_reportdate=True)
        self.assertEqual(state,'PAIR_RECOVERED');self.assertIsNone(row.reported_at)
        self.assertEqual(result['maximo']['actual_backfill']['scope_basis'],'EXACT_ID_SOURCE_ACTUAL_INTERVAL_REPORTDATE_UNKNOWN')
    def test_unknown_reportdate_exception_cannot_admit_old_future_or_bad_clocks(self):
        for a,b in [('2020-01-01T00:00:00Z','2020-01-02T00:00:00Z'),('2027-01-01T00:00:00Z','2027-01-02T00:00:00Z'),('2021-01-01T00:00:00','2021-01-02T00:00:00Z'),('2021-01-03T00:00:00Z','2021-01-02T00:00:00Z')]:
            result=pure_recovery(make_row(reported_at=None),raw(reportdate=None,actstart=a,actfinish=b),observed_at=NOW,run_id='test',ceiling=NOW,allow_unknown_reportdate=True)
            self.assertEqual(result,(None,'SOURCE_REPORTDATE_UNKNOWN'))
    def test_unknown_reportdate_exception_does_not_override_known_local_date(self):
        result=pure_recovery(make_row(),raw(reportdate=None),observed_at=NOW,run_id='test',ceiling=NOW,allow_unknown_reportdate=True)
        self.assertEqual(result,(None,'SOURCE_REPORTDATE_UNKNOWN'))
    def test_prioritization_handles_explicit_unknown_date_last(self):
        rows=[{'id':'BSR22/UNKNOWN','reported_at':None},{'id':'BSR21/OLD','reported_at':REPORT}]
        self.assertEqual(prioritize_pending(rows,NOW)[-1]['id'],'BSR22/UNKNOWN')
    def test_local_scope_conflict(self):self.assertEqual(self.recover(make_row(sources={'maximo':{'siteid':'OTHER'}})),(None,'LOCAL_SCOPE_CONFLICT'))
class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
        self.db=Database(DbConfig('sqlite+pysqlite:///:memory:'));self.db.create_all()
        with self.db.session() as s:
            s.add(make_row());s.add(EquipmentOrm(id='ASSET-1',sources={'maximo':{'assetnum':'ASSET-1','siteid':'BSR','orgid':'IP'}}));s.commit()
        create_plan(self.db,self.directory);self.plan=load_plan(self.directory)
    def tearDown(self):self.db.engine.dispose();self.temp.cleanup()
    def apply(self):return apply_batch(self.db,[raw()],self.plan['cohort'],self.directory,1,self.plan)
    def test_only_sources_change_and_backup_preserved(self):
        with self.db.session() as s:
            before={c.name:deepcopy(getattr(s.get(WorkOrderOrm,'BSR21/10001'),c.name)) for c in WorkOrderOrm.__table__.columns}
        self.apply();journal=json.loads((self.directory/'batch-000001.json').read_text())
        self.assertEqual(journal['state'],'COMMITTED');self.assertEqual(journal['changes'][0]['before'],before['sources'])
        with self.db.session() as s:
            row=s.get(WorkOrderOrm,'BSR21/10001');self.assertTrue(all(getattr(row,k)==v for k,v in before.items() if k!='sources'));self.assertEqual(s.query(SyncCursorOrm).count(),0)
        done,counts=reconcile_journals(self.db,self.directory);self.assertEqual(done,{'BSR21/10001'});self.assertEqual(counts['PAIR_RECOVERED'],1)
    def test_backup_failure_rolls_back(self):
        with patch('src.services.workorder_actual_backfill.save_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.apply()
        with self.db.session() as s:self.assertNotIn('actual_dates',s.get(WorkOrderOrm,'BSR21/10001').sources['maximo'])
    def test_batch_intrusion_rejected_before_write(self):
        with self.assertRaises(ValueError):apply_batch(self.db,[raw(),raw(wonum='OTHER')],self.plan['cohort'],self.directory,1,self.plan)
        self.assertFalse(list(self.directory.glob('batch-*.json')))
    def test_local_core_race_skip(self):
        with self.db.session() as s:s.get(WorkOrderOrm,'BSR21/10001').status='APPR';s.commit()
        doc=self.apply();self.assertEqual(doc['changes'],[]);self.assertEqual(doc['outcomes'][0]['result'],'LOCAL_CHANGED_SINCE_PLAN')
    def test_uncertain_commit_reconcile(self):
        self.apply();path=self.directory/'batch-000001.json';doc=json.loads(path.read_text());doc['state']='PREPARED';path.write_text(json.dumps(doc))
        self.assertEqual(reconcile_journals(self.db,self.directory)[0],{'BSR21/10001'});self.assertEqual(json.loads(path.read_text())['state'],'COMMITTED')
    def test_local_projection(self):
        self.apply();CollectorMartProjector(self.db,self.db).project_all()
        with self.db.session() as s:
            row=s.query(MaintenanceEventMartOrm).one();self.assertEqual(row.duration_hours,2.5);self.assertIsNotNone(row.actual_start);self.assertIsNotNone(row.actual_finish);self.assertEqual(row.sources['maximo']['scope_evidence'],'DIRECT_SOURCE');self.assertEqual(s.query(SyncCursorOrm).count(),0)
    def test_tampering_fail(self):
        path=self.directory/'cohort.json';doc=json.loads(path.read_text());doc['cohort'][0]['id']='OTHER';path.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):load_plan(self.directory)
    def test_unknown_date_exception_cannot_name_outside_cohort(self):
        path=self.directory/'cohort.json';doc=json.loads(path.read_text());doc.pop('sha256')
        doc['reportdate_unknown_exceptions']=['BSR22/OTHER'];doc['sha256']=digest(doc);path.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):load_plan(self.directory)
    def test_runtime_prefix_exclusion_stops_before_source_lock(self):
        from types import SimpleNamespace
        with patch('src.config.MaximoConfig.from_environment',return_value=SimpleNamespace(wo_prefixes=('BSR26',))):
            with self.assertRaisesRegex(ValueError,'COHORT_OUTSIDE_CONFIGURED_PREFIXES'):run(self.db,self.directory)
    def test_hard_limits(self):
        for batch,cap in [(101,1),(1,101),(0,1),(1,0)]:
            with self.assertRaises(ValueError):run(self.db,self.directory,batch_size=batch,max_batches=cap)
if __name__=='__main__':unittest.main()

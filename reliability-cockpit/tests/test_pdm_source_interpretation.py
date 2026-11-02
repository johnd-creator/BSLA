"""Sanitized, in-memory fixtures only; no real workbook values or services."""
import copy
import json
import unittest
from types import SimpleNamespace
from sqlalchemy import create_engine, select, event
from src.domain.engineering import Principal, Role, EngineeringError
from src.repositories.pdm_source_history import metadata, Source, Profile, Cell, Event
from src.services.pdm_source_history import SourceHistoryService, digest
from src.services.pdm_source_interpretation import BC_SHA, FAN_SHA, date_claim, interpret


class InterpretationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        metadata.create_all(self.engine)
        self.actor = Principal(principal_id='fixture-author', roles={Role.AUTHOR}, asset_ids={'asset:FIXTURE'})
        self.gates = []
        inspections = SimpleNamespace(repo=SimpleNamespace(engine=self.engine), gate=lambda actor:self.gates.append(actor.principal_id))
        self.service = SourceHistoryService(inspections, enabled=True)
        self.fields = [{'field_id':'field-l2','cell':'L23','role':'INPUT'}]
        self.doc = {'fields':self.fields,'clock_cells':['A23'],'clocks':[], 'source_asset_label':'BC 43',
                    'mapping':'UNVERIFIED_SOURCE_LABEL_ONLY','reasons':['SOURCE_DATE_UNRESOLVED'],'kind':'MEASUREMENT_SOURCE','classification':'RAW_UNRESOLVED'}
        self.profile = {'id':'wb-vib-bc-s003-b01','version':'fixture','fields':[{'id':'field-l2','source_label':'4H','unit':None,'header_cells':['L2']} ]}
        ph = digest(self.profile)
        self.row = dict(event_key='1'*64,owner_id=self.actor.principal_id,access_asset_id='asset:FIXTURE',source_sha=BC_SHA,source_ref='WB-VIB-BC',sheet_index=2,
                        profile_id=self.profile['id'],profile_hash=ph,axis='ROW',position=23,classification_hash='c'*64,kind='MEASUREMENT_SOURCE',classification='RAW_UNRESOLVED',document=self.doc)
        self.cells = {a:{'raw_value':v,'source_type':'s' if isinstance(v,str) else 'n'} for a,v in
                      {'A1':'TANGGAL','B1':'BC 43 - mm/s','L2':'4H','A22':20210421,'A23':20210520,'A24':20210617,'L22':1.0,'L24':3.0}.items()}
        self.anchors=[]
        for pos,key in [(22,'2'),(24,'3')]:
            row=copy.deepcopy(self.row);row.update(event_key=key*64,position=pos)
            row['document']['fields']=[{'field_id':'field-l2','cell':f'L{pos}','role':'INPUT'}];row['document']['clock_cells']=[f'A{pos}'];self.anchors.append(row)
        with self.engine.begin() as c:
            c.execute(Source.insert().values(source_sha=BC_SHA,document={'sheets':[{}, {}, {'label':'BC 43'}]}))
            c.execute(Profile.insert().values(profile_hash=ph,document=self.profile))
            c.execute(Event.insert(),[self.row,*self.anchors])
            c.execute(Cell.insert(),[dict(source_sha=BC_SHA,sheet_index=2,coordinate=a,terminal_role='CONTEXT',claims=[],document=v) for a,v in self.cells.items()])
    def tearDown(self):self.engine.dispose()
    def detail(self):return self.service.detail(self.actor,self.row['event_key'])
    def fields_for_pure(self,raw=None,**extra):return [dict(self.fields[0],value={'raw_value':raw,**extra})]
    def overlay(self,cells=None,anchors=None,row=None,fields=None):
        return interpret(row or self.row,fields or self.fields_for_pure(),self.cells if cells is None else cells,self.anchors if anchors is None else anchors)
    def test_reviewed_gap_is_separate_and_reads_do_not_write(self):
        statements=[]
        event.listen(self.engine,'before_cursor_execute',lambda conn,cursor,statement,parameters,context,executemany:statements.append(statement))
        original=copy.deepcopy((self.row,self.cells,self.fields,self.anchors))
        detail=self.detail();derived=detail['derived_interpretation'];estimate=derived['fields'][0]['estimate']
        self.assertEqual(detail['fields'][0]['value']['raw_value'],None)
        self.assertAlmostEqual(estimate['value'],1+(3-1)*29/57)
        self.assertEqual(estimate['label'],'ESTIMASI');self.assertEqual(estimate['confidence'],'LOW')
        self.assertEqual(derived['date']['value'],'2021-05-20');self.assertFalse(derived['canonical_eligible']);self.assertFalse(derived['persisted'])
        self.assertEqual(detail['item']['classification'],'RAW_UNRESOLVED');self.assertFalse(detail['editable'])
        self.assertTrue(all(s.lstrip().upper().startswith(('SELECT','PRAGMA')) for s in statements))
        self.assertEqual(original,(self.row,self.cells,self.fields,self.anchors))
    def test_hidden_neighbor_owner_prevents_estimate_and_proof_leak(self):
        with self.engine.begin() as c:c.execute(Event.update().where(Event.c.position==22).values(owner_id='hidden'))
        d=self.detail()['derived_interpretation'];self.assertNotIn('estimate',d['fields'][0]);self.assertNotIn('L22',json.dumps(d))
    def test_hidden_neighbor_asset_prevents_estimate(self):
        with self.engine.begin() as c:c.execute(Event.update().where(Event.c.position==24).values(access_asset_id='foreign'))
        self.assertNotIn('estimate',self.detail()['derived_interpretation']['fields'][0])
    def test_unauthorized_target_never_loads_context(self):
        actor=self.actor.model_copy(update={'principal_id':'other'})
        statements=[];event.listen(self.engine,'before_cursor_execute',lambda conn,cursor,s,p,ctx,m:statements.append(s))
        with self.assertRaisesRegex(EngineeringError,'NOT_FOUND'):self.service.detail(actor,self.row['event_key'])
        self.assertFalse(any('FROM nadi_history_cell' in s for s in statements))
    def test_reviewer_cannot_gain_history(self):
        actor=self.actor.model_copy(update={'roles':frozenset({Role.REVIEWER})})
        with self.assertRaisesRegex(EngineeringError,'AUTHOR_SCOPE'):self.service.detail(actor,self.row['event_key'])
    def test_source_hash_or_profile_change_disables_rules(self):
        for change in ({'source_sha':'f'*64},{'profile_id':'different'},{'sheet_index':3},{'source_ref':'WB-OTHER'},{'axis':'COL'},{'kind':'RAW_SOURCE_ROW'}):
            with self.subTest(change=change):self.assertIsNone(self.overlay(row={**self.row,**change}))
    def test_header_unit_or_point_conflict_prevents_estimate(self):
        for a,v in [('B1','BC 43 - mils'),('A1','TIME'),('L2','5H')]:
            cells=copy.deepcopy(self.cells);cells[a]['raw_value']=v;result=self.overlay(cells=cells)
            self.assertTrue(result is None or all('estimate' not in f for f in result['fields']))
    def test_present_zero_empty_text_and_formula_never_replaced(self):
        for raw in (0,False,'',1.0):
            self.assertNotIn('estimate',self.overlay(fields=self.fields_for_pure(raw))['fields'][0])
        self.assertNotIn('estimate',self.overlay(fields=self.fields_for_pure(formula_present=True))['fields'][0])
    def test_formula_nonfinite_boolean_and_missing_anchors_fail_closed(self):
        for value in (True,None,float('nan'),float('inf'),'1.0'):
            cells=copy.deepcopy(self.cells);cells['L22']['raw_value']=value
            self.assertNotIn('estimate',self.overlay(cells=cells)['fields'][0])
        cells=copy.deepcopy(self.cells);cells['L22']['formula_present']=True
        self.assertNotIn('estimate',self.overlay(cells=cells)['fields'][0])
        for anchors in ([],self.anchors[:1],[*self.anchors,self.anchors[0]]):
            self.assertNotIn('estimate',self.overlay(anchors=anchors)['fields'][0])
    def test_duplicate_date_wrong_gap_and_extrapolation_refused(self):
        for a,v in [('A22',20210617),('A24',20210421),('A23',20211201),('A22',20210420)]:
            cells=copy.deepcopy(self.cells);cells[a]['raw_value']=v
            self.assertNotIn('estimate',self.overlay(cells=cells)['fields'][0])
    def test_no_estimate_for_other_blanks_or_reclassified_anchor(self):
        fields=[{'field_id':'field-m2','cell':'M23','value':{'raw_value':None}}];cells=copy.deepcopy(self.cells);cells['M2']={'raw_value':'4A'}
        self.assertNotIn('estimate',self.overlay(fields=fields,cells=cells)['fields'][0])
        anchors=copy.deepcopy(self.anchors);anchors[0]['document']['fields'][0]['role']='REFERENCE'
        self.assertNotIn('estimate',self.overlay(anchors=anchors)['fields'][0])
    def test_reclassified_target_is_not_estimated(self):
        for role in ('REFERENCE','SOURCE_ASSESSMENT','CONTEXT','UNCLASSIFIED'):
            with self.subTest(role=role):
                with self.engine.begin() as c:
                    doc=copy.deepcopy(self.doc);doc['fields'][0]['role']=role
                    c.execute(Event.update().where(Event.c.event_key==self.row['event_key']).values(document=doc))
                derived=self.detail()['derived_interpretation']['fields'][0]
                self.assertEqual(derived['unit'],'mm/s')
                self.assertNotIn('estimate',derived)
    def test_duplicate_anchor_event_is_bounded_and_refused(self):
        row=copy.deepcopy(self.anchors[0]);row['event_key']='4'*64
        with self.engine.begin() as c:c.execute(Event.insert(),row)
        self.assertNotIn('estimate',self.detail()['derived_interpretation']['fields'][0])
    def test_date_parser_requires_literal_exact_unambiguous_calendar(self):
        self.assertEqual(str(date_claim({'raw_value':20240229,'source_type':'n'})),'2024-02-29')
        for raw in (20230229,20241301,20210520.0,True,'20/05/2021',' 20210520',99991231,None):
            self.assertIsNone(date_claim({'raw_value':raw,'source_type':'n'}))
        self.assertIsNone(date_claim({'raw_value':20210520,'source_type':'n','formula_present':True}))
    def fan(self,pos=10):
        row={**self.row,'source_sha':FAN_SHA,'source_ref':'WB-FAN','sheet_index':0,'profile_id':'wb-fan-s001-b01','position':pos}
        cells={a:{'raw_value':v} for a,v in {'J7':'Ferrous','J8':'(ppm)','G7':' Viscosity Change\n(%)','G8':'Viscosity (Cst)','H8':'Result','K8':'S (sulfur)','K9':'(ppm)'}.items()}
        fields=[{'field_id':c,'cell':f'{c}{pos}','value':{'raw_value':None}} for c in ('J','G','H','K')]
        return row,cells,fields
    def test_subheader_ppm_and_distinct_viscosity_units(self):
        row,cells,fields=self.fan();before=copy.deepcopy((row,cells,fields));d=interpret(row,fields,cells)
        self.assertEqual([f['unit'] for f in d['fields']],['ppm','Cst','%','ppm'])
        self.assertEqual(before,(row,cells,fields));self.assertFalse(any('estimate'in f for f in d['fields']))
    def test_header_rows_are_context_and_never_estimated(self):
        for pos in (8,9):
            d=interpret(*self.fan_args(pos));self.assertEqual(d['row_context']['label'],'KONTEKS HEADER');self.assertEqual(d['fields'],[]);self.assertIsNone(d['date'])
    def fan_args(self,pos):
        row,cells,fields=self.fan(pos);return row,fields,cells
    def test_unreviewed_fan_date_and_rows_do_not_gain_inference(self):
        row,cells,fields=self.fan(7);self.assertIsNone(interpret(row,fields,cells))
        row,cells,fields=self.fan();cells['J8']['raw_value']='(unknown)';d=interpret(row,fields,cells);self.assertFalse(any(f['cell']=='J10' for f in d['fields']))


if __name__ == '__main__':unittest.main()

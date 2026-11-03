"""Safe, source-bound timestamp expressions for SQL-only WO aggregates.

PostgreSQL16 verifies calendar inputs before casts. SQLite is the disposable
fixture dialect; julianday comparisons use its millisecond clock resolution.
No source text receives an invented timezone and no malformed JSON is cast.
"""
from sqlalchemy import and_,case,cast,DateTime,Numeric,func,literal

ISO=r'^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,9})?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$'
MIN_EPOCH=-62135596800
MAX_EPOCH=253402300800

class WoProofSql:
 def __init__(self,database,scope):
  self.postgres=database.engine.dialect.name=='postgresql';self.scope=scope
  self.tolerance=.000002 if self.postgres else .001
 def json(self,*path):
  expr=self.scope.c.sources
  for part in path:expr=expr[part]
  return expr
 def kind(self,path):
  return func.jsonb_typeof(self.json(*path)) if self.postgres else func.json_type(self.scope.c.sources,'$.'+'.'.join(path))
 def number(self,path):
  kinds=('number',) if self.postgres else ('integer','real')
  return case((self.kind(path).in_(kinds),cast(self.json(*path).as_string(),Numeric())),else_=None)
 def schema(self,path):return self.number(path)==1
 def text(self,path):return case((self.kind(path)=='string' if self.postgres else self.kind(path)=='text',self.json(*path).as_string()),else_=None)
 def epoch(self,path):
  value=self.text(path)
  shape=and_(func.length(value)<=128,value.regexp_match(ISO),~value.like('%-00:00'))
  if self.postgres:
   valid=and_(shape,func.pg_input_is_valid(value,'timestamp with time zone'))
   return case((valid,func.extract('epoch',cast(value,DateTime(timezone=True)))),else_=None)
  # Verify the original calendar day before offset conversion. Invalid dates
  # such as February30 can otherwise normalize silently in SQLite.
  valid=and_(shape,func.strftime('%Y-%m-%d',func.substr(value,1,10),'+0 days')==func.substr(value,1,10))
  return case((valid,(func.julianday(value)-2440587.5)*86400.0),else_=None)
 def column_epoch(self,column):
  return func.extract('epoch',column) if self.postgres else (func.julianday(column)-2440587.5)*86400.0
 def same(self,left,right):return and_(left.is_not(None),right.is_not(None),func.abs(left-right)<=self.tolerance)
 def identity(self,path):
  return and_(self.schema((*path,'schema_version')),
   self.text((*path,'identity','wonum'))==self.text(('maximo','wonum')),
   self.text((*path,'identity','assetnum'))==self.text(('maximo','assetnum')),
   self.text((*path,'identity','siteid'))=='BSR',self.text((*path,'identity','orgid'))=='IP')
 def valid_actual(self,key,column):
  root=('maximo','actual_dates');path=(*root,'fields',key)
  original=self.epoch((*path,'original'));normalized=self.epoch((*path,'normalized'));observed=self.epoch((*path,'source_changed_at'));current=self.column_epoch(self.scope.c.source_changed_at)
  return and_(self.identity(root),self.text((*path,'state'))=='VALID',observed.is_not(None),current.is_not(None),observed<=current,
              self.same(original,normalized),self.same(normalized,self.column_epoch(column)))
 def reported(self):
  root=('maximo','wo_detail');path=(*root,'fields','reported_at')
  raw=self.number((*path,'epoch_seconds'))
  number=case((and_(raw>=MIN_EPOCH,raw<MAX_EPOCH),raw),else_=None)
  value=self.epoch((*path,'value'));observed=self.epoch((*path,'source_changed_at'));root_version=self.epoch((*root,'source_changed_at'));current=self.column_epoch(self.scope.c.source_changed_at)
  valid=and_(self.identity(root),self.same(root_version,current),observed.is_not(None),observed<=root_version,
             self.text((*path,'origin')).in_(['MAXIMO_RESPONSE','LEGACY_COLUMN']),
             self.text((*path,'state')).in_(['SOURCE_VALUE','RETAINED_LEGACY_VALUE']),self.same(value,number))
  return number,valid

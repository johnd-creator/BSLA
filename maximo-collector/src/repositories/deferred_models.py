"""B2 candidate-only SQL metadata. Never registered with operational Base."""
from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, String, Table

metadata = MetaData()

def string(name, size, *, nullable=False, primary_key=False):
    return Column(name, String(size), nullable=nullable, primary_key=primary_key)

def number(name, *, big=False):
    return Column(name, BigInteger if big else Integer, nullable=False)

def timestamp(name):
    return Column(name, DateTime(timezone=True), nullable=False)

family = Table('mart_deferred_family', metadata,
    string('id',64,primary_key=True), string('domain',40), string('source_system',16),
    string('source_object',30), string('source_id',60), string('scope_key',40),
    string('policy_epoch',64), string('mapper_epoch',64), string('current_id',36,nullable=True))
version = Table('mart_deferred_version', metadata,
    string('id',36,primary_key=True), string('family_id',64), number('version'), string('fingerprint',64),
    string('first_run',36), string('first_manifest',36), number('first_ordinal'), string('predecessor_id',36,nullable=True),
    string('scope_proof',16), string('site',20,nullable=True), string('organization',20,nullable=True),
    string('canonical_id',200,nullable=True), string('classification',40), string('reason',40),
    string('state',32), timestamp('first_at'), timestamp('last_attempt'), number('attempts'), number('revision'),
    string('last_event',36,nullable=True), string('resolution_event',36,nullable=True),
    string('superseded_by',36,nullable=True), number('fence',big=True), string('owner',36))
dependency = Table('mart_deferred_dependency', metadata,
    string('obligation_id',36,primary_key=True), string('kind',30,primary_key=True),
    string('scoped_key',240,primary_key=True))
event = Table('mart_deferred_event', metadata,
    string('id',36,primary_key=True), string('event_key',64), string('obligation_id',36),
    number('revision'), string('from_state',32,nullable=True), string('to_state',32),
    string('action',20), string('reason',40), string('evidence_run',36), number('evidence_ordinal'),
    string('target_digest',64,nullable=True), timestamp('at'), number('fence',big=True), string('owner',36))
occurrence = Table('mart_deferred_occurrence', metadata,
    string('run_id',36,primary_key=True), Column('ordinal',Integer,primary_key=True), string('obligation_id',36))

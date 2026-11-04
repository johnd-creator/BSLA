"""006 synthetic replay metadata; never part of operational Base/create_all."""
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, BigInteger
metadata = MetaData()
def string(name, size, nullable=False, primary_key=False):
    return Column(name, String(size), nullable=nullable, primary_key=primary_key)
def number(name, big=False):
    return Column(name, BigInteger if big else Integer, nullable=False)
queue = Table('mart_replay_queue',metadata,
    string('family_id',64,primary_key=True), string('obligation_id',36),
    string('domain',40), string('scope_key',40), string('policy_epoch',64),
    string('replay_epoch',64), string('policy_digest',64), string('phase',20), string('reason',40),
    Column('due_at',DateTime(timezone=True),nullable=False),
    number('probes'), number('attempts'), number('revision'),
    string('run_id',36,nullable=True), string('owner',36), number('fence',True))
event = Table('mart_replay_event',metadata,
    string('id',36,primary_key=True), string('family_id',64), string('obligation_id',36),
    number('revision'), string('phase',20), string('reason',40),
    number('probes'), number('attempts'), string('run_id',36,nullable=True),
    string('owner',36), number('fence',True), Column('at',DateTime(timezone=True),nullable=False))

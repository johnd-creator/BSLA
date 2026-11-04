"""B1 candidate metadata, deliberately separate from operational Base/create_all.

Only the reviewed additive SQL migration installs these tables and guards.
Importing this module does not install or migrate anything.
"""
from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, Table, Text)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
lease = Table(
    "mart_capture_domain", metadata,
    Column("domain", String(40), primary_key=True),
    Column("fence", BigInteger, nullable=False),
    Column("owner", String(36), nullable=False),
    Column("lease_until", DateTime(timezone=True), nullable=False),
    Column("latest_run", String(36)),
    Column("last_complete_run", String(36)),
    Column("last_complete_at", DateTime(timezone=True)),
)
run = Table(
    "mart_capture_run", metadata,
    Column("id", String(36), primary_key=True),
    Column("manifest_id", String(36), unique=True, nullable=False),
    Column("domain", String(40), ForeignKey(lease.c.domain), nullable=False),
    Column("epoch", String(64), nullable=False),
    Column("scope", JSONB, nullable=False),
    Column("sealed", Boolean, nullable=False),
    Column("item_count", Integer, nullable=False),
    Column("byte_count", BigInteger, nullable=False),
    Column("manifest_digest", String(64)),
    Column("snapshot", Text),
    Column("continuation", Integer, nullable=False),
    Column("status", String(20), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)
item = Table(
    "mart_capture_item", metadata,
    Column("run_id", String(36), ForeignKey(run.c.id), primary_key=True),
    Column("ordinal", Integer, primary_key=True),
    Column("source_id", String(60), nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("disposition", String(30)),
    Column("reason", String(40)),
    Column("acked_at", DateTime(timezone=True)),
    Column("target_id", String(200)),
    Column("target_digest", String(64)),
)
target = Table(
    "mart_capture_target", metadata,
    Column("domain", String(40), primary_key=True),
    Column("canonical_id", String(200), primary_key=True),
    Column("fence", BigInteger, nullable=False),
    Column("run_id", String(36), ForeignKey(run.c.id), nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("target_digest", String(64), nullable=False),
)

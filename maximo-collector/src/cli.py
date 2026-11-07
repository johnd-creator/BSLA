#!/usr/bin/env python3
"""CLI for the Maximo collector.

Read-only against Maximo (auto-login per maximo-knowledge recipe). Commands:
  init-db         - create collector local tables
  sync [objects]  - sync operational objects (asset refresh is explicit)
  diagnose master-data - GET-only access diagnosis for Persons, Items, Labor
  serve           - start the FastAPI app on :8002

Credentials come from the environment (.env): MAXIMO_USERNAME/MAXIMO_PASSWORD
(login mode) or MAXIMO_READ_ONLY_TOKEN (token mode).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone

from src.config import MaximoConfig, load_env
from src.repositories.database import get_database
from src.repositories.store import CollectorStore

load_env()

LOG = logging.getLogger(__name__)

AVAILABLE_OBJECTS = ["mxapiasset", "mxwodetail", "mxapisr", "mxperson", "mxitem", "mxapilabor"]
DEFAULT_OBJECTS = ["mxwodetail", "mxapisr", "mxapilabor", "mxperson", "mxitem"]


def _safe_error_text(value: object) -> str:
    text = re.sub(r"https?://\S+", "<url>", str(value))
    text = re.sub(r"'[^']*'", "'<redacted>'", text)
    text = re.sub(r'"[^"]*"', '"<redacted>"', text)
    return text[:300]


def _safe_error_metadata(error: Exception) -> dict[str, object]:
    response = getattr(error, "response", None)
    error_class = type(error).__name__
    metadata: dict[str, object] = {
        "error_class": error_class,
        "error_category": (
            "READ_TIMEOUT" if error_class in {"ReadTimeout", "ConnectTimeout", "Timeout", "TimeoutError"}
            else "UNKNOWN"
        ),
    }
    if response is None:
        return metadata
    http_status = getattr(response, "status_code", None)
    metadata.update({
        "http_status": http_status,
        "content_type": response.headers.get("Content-Type", "").split(";", 1)[0],
        "response_bytes": len(response.content),
    })
    if http_status == 500:
        metadata["error_category"] = "UPSTREAM_MAXIMO_500"
    try:
        payload = response.json()
    except ValueError:
        return metadata

    def walk(value: object, prefix: str = "") -> dict[str, str]:
        found: dict[str, str] = {}
        if isinstance(value, dict):
            for key, child in value.items():
                name = f"{prefix}.{key}" if prefix else str(key)
                if isinstance(child, (str, int, float, bool)) and any(
                    marker in str(key).lower()
                    for marker in ("error", "code", "message", "reason", "status")
                ):
                    found[name] = _safe_error_text(child)
                else:
                    found.update(walk(child, name))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found.update(walk(child, f"{prefix}[{index}]"))
        return found

    metadata["sanitized_error_fields"] = walk(payload)
    return metadata


def _sync_service(store: CollectorStore):
    from src.adapters.maximo.auth import MaximoAuth
    from src.adapters.maximo.oslc_client import OslcClient
    from src.services.sync import SyncService

    config = MaximoConfig.from_environment()
    client = OslcClient(config, MaximoAuth(config))
    return SyncService(client, store, site_id=config.site_id), config


def cmd_init_db(args: argparse.Namespace) -> int:
    db = get_database()
    db.create_all()
    seeded = CollectorStore(db).seed_equipment_status_history()
    print("maximo-collector local tables created (Postgres)")
    if seeded:
        print(f"seeded {seeded} existing equipment status observations")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from src.api.app import sync_config_for

    store = CollectorStore(get_database())
    service, config = _sync_service(store)

    selected = args.objects or DEFAULT_OBJECTS
    exit_code = 0
    for name in selected:
        try:
            cfg = sync_config_for(name)
        except KeyError:
            print(f"unknown object: {name} (available: {', '.join(AVAILABLE_OBJECTS)})")
            exit_code = 1
            continue
        try:
            started_at = datetime.now(timezone.utc).isoformat()
            stats = service.sync(cfg)
        except Exception as error:  # noqa: BLE001 — report one object failure and continue
            metadata = _safe_error_metadata(error)
            metadata.update({
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "page": getattr(error, "page", None),
            })
            LOG.error(
                "sync failure object_structure=%s outcome=failed metadata=%s",
                name,
                metadata,
            )
            exit_code = 1
            continue
        complete = getattr(stats, "complete", True)
        print(
            f"{stats.mode} sync {stats.object_structure}: "
            f"{stats.rows_seen} seen, {stats.upserted} upserted, "
            f"{stats.skipped} skipped, {stats.errors} errors, "
            f"complete={complete}, watermark={stats.watermark}"
        )
        if getattr(stats, "recency", None):
            print(json.dumps(stats.recency, sort_keys=True))
        if not complete:
            exit_code = 1
    return exit_code


def cmd_bootstrap_workorders_recent(args: argparse.Namespace) -> int:
    """Recover the missing WO tail with explicit finite operator ceilings."""
    from src.api.app import sync_config_for
    from src.services.workorder_recency import bootstrap_recent_work_orders
    store = CollectorStore(get_database())
    service, _config = _sync_service(store)
    routine = sync_config_for("mxwodetail")
    config = replace(routine, page_size=args.page_size, max_pages=args.max_pages,
                     request_limit=args.request_budget)
    try:
        stats = bootstrap_recent_work_orders(service._client, store, config)
    except Exception as error:
        print(json.dumps({"stop_reason": "BOOTSTRAP_STORE_OR_CONFIG_ERROR",
                          "error_class": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps(stats.recency, sort_keys=True))
    if not stats.complete:
        return 2
    followup = service.sync(routine)
    print(json.dumps({"routine_verification": followup.recency}, sort_keys=True))
    return 0 if followup.complete else 2


def _bootstrap_limit(maximum):
    def parse(value):
        try:
            number = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("expected an integer") from error
        if not 1 <= number <= maximum:
            raise argparse.ArgumentTypeError(f"expected a value between 1 and {maximum}")
        return number
    return parse


def cmd_backfill(args: argparse.Namespace) -> int:
    """Run an idempotent, cursor-independent BSR work-order traversal."""
    from src.api.app import sync_config_for

    store = CollectorStore(get_database())
    service, _config = _sync_service(store)
    config = replace(
        sync_config_for("mxwodetail"),
        watermark_field=None,
        recent_work_orders=False,
        order_by=None,
        # The verified site scope plus the accepted Maximo IN-prefix filter
        # bounds the historical traversal to BSR work-order keys. The prefix
        # is still validated client-side as a second safety boundary.
        prefix_query=True,
        page_size=args.page_size,
        max_pages=args.max_pages,
    )
    stats = service.sync(config)
    print(
        f"backfill {stats.object_structure}: {stats.rows_seen} seen, "
        f"{stats.upserted} upserted, {stats.skipped} skipped, "
        f"{stats.errors} errors, complete={stats.complete}, "
        f"pagination_error={stats.pagination_error}"
    )
    return 0 if stats.complete else 2


def cmd_repair_asset_coverage(args: argparse.Namespace) -> int:
    """Run one bounded, cursor-safe current MXAPIASSET baseline."""
    from src.services.asset_baseline import AssetBaselineBlocked, run_asset_baseline

    registry_file = args.registry_file or os.environ.get("MAXIMO_ASSET_REGISTRY_FILE")
    if not registry_file:
        print(json.dumps({"status": "BLOCKED", "reason": "REGISTRY_FILE_REQUIRED"}, sort_keys=True))
        return 2
    try:
        result = run_asset_baseline(
            registry_file,
            get_database(),
            dry_run=args.dry_run,
            page_size=args.page_size,
            max_pages=args.max_pages,
            request_budget=args.request_budget,
        )
    except AssetBaselineBlocked as error:
        print(json.dumps({"status": "BLOCKED", "reason": error.reason}, sort_keys=True))
        return 2
    except Exception as error:  # sanitized operator output; never echo source values
        print(json.dumps({"status": "FAILED", "error": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"COMPLETE", "DRY_RUN"} else 2


def cmd_repair_asset_registry_residuals(args: argparse.Namespace) -> int:
    """Complete only the current registry residuals with exact GETs."""
    from src.services.asset_registry_residual import (
        AssetRegistryResidualBlocked,
        run_asset_registry_residual_repair,
    )

    registry_file = args.registry_file or os.environ.get("MAXIMO_ASSET_REGISTRY_FILE")
    if not registry_file:
        print(json.dumps({"status": "BLOCKED", "reason": "REGISTRY_FILE_REQUIRED"}, sort_keys=True))
        return 2
    try:
        result = run_asset_registry_residual_repair(
            registry_file,
            get_database(),
            dry_run=args.dry_run,
        )
    except AssetRegistryResidualBlocked as error:
        print(json.dumps({"status": "BLOCKED", "reason": error.reason}, sort_keys=True))
        return 2
    except Exception as error:  # sanitized operator output; never echo source values
        print(json.dumps({"status": "FAILED", "error": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"COMPLETE", "DRY_RUN"} else 2


def cmd_run(args: argparse.Namespace) -> int:
    """Run independent read-only sync loops for operational and asset data.

    Assets intentionally have a slower cadence: Maximo operational changes are
    normally work-order driven, while an asset refresh is a master-data task.
    A failure in one cycle is logged; the next scheduled cycle still runs.
    """
    stop = threading.Event()

    def _stop(signum, frame):
        LOG.info("received signal %s, shutting down scheduler", signum)
        stop.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    def _loop(name: str, objects: list[str], interval: int) -> None:
        while not stop.is_set():
            result = cmd_sync(argparse.Namespace(objects=objects))
            if result:
                LOG.warning("%s sync cycle finished with exit code %s", name, result)
            stop.wait(interval)

    LOG.info(
        "starting read-only Maximo scheduler: operational every %ss; assets every %ss",
        args.operational_interval_seconds,
        args.asset_interval_seconds,
    )
    workers = [
        threading.Thread(
            target=_loop,
            args=("operational", DEFAULT_OBJECTS, args.operational_interval_seconds),
            daemon=True,
        ),
        threading.Thread(
            target=_loop,
            args=("asset", ["mxapiasset"], args.asset_interval_seconds),
            daemon=True,
        ),
    ]
    for worker in workers:
        worker.start()
    while not stop.wait(1):
        pass
    for worker in workers:
        worker.join(timeout=5)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from src.api.app import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Probe verified master-data scopes without writing to the local store."""
    from src.adapters.maximo.oslc_client import OslcClient
    from src.adapters.maximo.auth import MaximoAuth

    config = MaximoConfig.from_environment()
    client = OslcClient(config, MaximoAuth(config))
    probes = (
        ("mxperson", 'locationorg="IP"', "statusdate", ("personid", "displayname", "firstname", "status", "statusdate", "locationorg")),
        ("mxitem", 'site="BSR"', "statusdate", ("itemnum", "description", "status", "site")),
        ("mxapilabor", 'worksite="BSR"', None, ("laborcode", "personid", "status", "worksite")),
    )
    exit_code = 0
    for object_structure, scope, order_by, fields in probes:
        sample_count = 0
        fields_seen: set[str] = set()
        try:
            for member in client.iterate(
                object_structure,
                where=scope,
                required_scope=scope,
                select=list(fields),
                order_by=f"-{order_by}" if order_by else None,
                max_pages=1,
            ):
                sample_count += 1
                fields_seen.update(field for field in fields if member.get(field) is not None)
                if sample_count >= 3:
                    break
            result = "available" if sample_count else "zero_rows"
            print(
                f"{object_structure}: {result}; scope={scope}; "
                f"sample_count={sample_count}; fields_seen={sorted(fields_seen)}"
            )
            if not sample_count:
                exit_code = 2
        except Exception as error:  # noqa: BLE001 — diagnosis must continue per object
            exit_code = 1
            print(f"{object_structure}: error; scope={scope}; {type(error).__name__}: {error}")
    return exit_code


def cmd_profile_workorders(args: argparse.Namespace) -> int:
    """Profile bounded MXWODETAIL slices without local-store or Mart writes."""
    from src.adapters.maximo.auth import MaximoAuth
    from src.adapters.maximo.oslc_client import OslcClient
    from src.services.workorder_profile import WorkOrderPopulationProfiler

    try:
        config = MaximoConfig.from_environment()
        client = OslcClient(config, MaximoAuth(config), request_budget=args.request_budget)
        profiler = WorkOrderPopulationProfiler(
            client,
            source_cap=args.source_cap,
            page_size=args.page_size,
            max_pages=args.max_pages,
            prefixes=config.wo_prefixes,
        )
        if args.mode == "default-source":
            result = {"default": profiler.profile_source(None).as_dict()}
        elif args.mode == "recent-source":
            probe = profiler.probe_recent_order()
            result = {"recent_order_probe": probe.as_dict()}
            if probe.supported:
                result["recent"] = profiler.profile_source("-changedate").as_dict()
        else:
            result = profiler.compare()
        result["request_telemetry"] = client.request_telemetry
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as error:  # sanitized aggregate profiler failure
        print(json.dumps({"error": _safe_error_metadata(error)}, sort_keys=True))
        return 2


def cmd_reconcile_asset_registry(args: argparse.Namespace) -> int:
    """Reconcile a local List of Assets export with local Collector/Mart data."""
    from src.services.asset_registry_reconciliation import (
        load_local_reconciliation_input,
        parse_registry_file,
        reconcile_registry,
        verify_missing_registry_sample,
    )

    registry_file = args.registry_file or os.environ.get("MAXIMO_ASSET_REGISTRY_FILE")
    if not registry_file:
        print(json.dumps({"error": "REGISTRY_FILE_REQUIRED"}, sort_keys=True))
        return 2
    try:
        registry = parse_registry_file(registry_file)
        local = load_local_reconciliation_input(get_database())
        result = reconcile_registry(registry, local)
        if getattr(args, "verify_missing", False):
            from src.adapters.maximo.auth import MaximoAuth
            from src.adapters.maximo.oslc_client import OslcClient

            config = MaximoConfig.from_environment()
            client = OslcClient(config, MaximoAuth(config), request_budget=20)
            result["optional_maximo_verification"] = verify_missing_registry_sample(
                registry.records,
                {row.id for row in local.equipment},
                client,
                sample_size=args.sample_size,
            )
        else:
            result["optional_maximo_verification"] = {"executed": False}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as error:  # aggregate-only command; never echo file/row values
        print(json.dumps({"error": type(error).__name__}, sort_keys=True))
        return 2


def cmd_mart_load(args: argparse.Namespace) -> int:
    """Run the explicit, bounded initial Reliability Mart profile."""
    from src.adapters.maximo.auth import MaximoAuth
    from src.adapters.maximo.oslc_client import OslcClient
    from src.services.canonical import CanonicalCollector
    from src.services.controlled_mart_load import (
        CONTROLLED_REQUEST_BUDGET,
        ControlledMartLoader,
        resolve_profile,
        resolve_source,
        verify_mart_database,
    )
    from src.services.mart import MartWriter

    try:
        profile = resolve_profile(args.profile)
        source = resolve_source(args.entity) if args.entity else None
        config = MaximoConfig.from_environment()
        db = get_database()
        verify_mart_database(db, config)
    except Exception as error:  # sanitized preflight failure
        print(f"mart-load blocked: {type(error).__name__}")
        return 2

    auth = MaximoAuth(config)
    client = OslcClient(config, auth, request_budget=CONTROLLED_REQUEST_BUDGET)
    collector = CanonicalCollector(client, runtime_config=config)
    loader = ControlledMartLoader(
        collector,
        MartWriter(db),
        CollectorStore(db),
        config,
        profile=profile,
    )
    try:
        result = loader.run(
            dry_run=args.dry_run,
            source=source,
            source_cap_override=args.record_cap,
        )
    except Exception as error:  # sanitized argument/preflight failure
        print(f"mart-load blocked: {type(error).__name__}")
        return 2
    for report in result.reports:
        print(
            f"{report.source}: read={report.source_records_read} "
            f"emitted={report.canonical_records_emitted} "
            f"skipped={report.records_skipped} "
            f"inserted={report.inserted} updated={report.updated} "
            f"unchanged={report.unchanged} pages={report.pages} "
            f"completeness={report.completeness}"
            + (f" failure={report.failure_class}" if report.failure_class else "")
        )
    telemetry = client.request_telemetry
    print(
        f"mart-load profile={profile.name} dry_run={args.dry_run} "
        f"business_requests={telemetry['business_requests']} "
        f"status_counts={telemetry['status_counts']} "
        f"stopped={result.stopped}"
    )
    if result.stop_reason:
        print(f"stop_reason={result.stop_reason}")
    failed = any(report.completeness == "FAILED" for report in result.reports)
    return 2 if result.stopped or failed else 0


def _local_mart_database():
    """Build the downstream writer DB without constructing a Maximo client."""
    from src.services.local_mart_projector import mart_write_database

    return mart_write_database()


def cmd_mart_import_asset_registry(args: argparse.Namespace) -> int:
    """Activate a validated local List of Assets snapshot in the Mart."""
    from src.services.asset_registry_reconciliation import parse_registry_file
    from src.services.local_mart_projector import import_registry_snapshot

    registry_file = args.registry_file or os.environ.get("MAXIMO_ASSET_REGISTRY_FILE")
    if not registry_file:
        print(json.dumps({"status": "BLOCKED", "reason": "REGISTRY_FILE_REQUIRED"}, sort_keys=True))
        return 2
    try:
        snapshot = parse_registry_file(registry_file)
        result = import_registry_snapshot(
            snapshot,
            get_database(),
            _local_mart_database(),
            expected_sha256=args.expected_sha256,
            dry_run=args.dry_run,
        )
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps({"status": "DRY_RUN" if args.dry_run else "COMPLETE", **result}, indent=2, sort_keys=True))
    return 0


def cmd_mart_project(args: argparse.Namespace) -> int:
    """Project local Collector rows into the Mart; this command is LOCAL ONLY."""
    from src.services.local_mart_projector import CollectorMartProjector

    try:
        projector = CollectorMartProjector(get_database(), _local_mart_database(), batch_size=args.batch_size)
        result = projector.project_all(incremental=args.incremental)
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps({"status": "COMPLETE", "mode": "incremental" if args.incremental else "full", **result}, indent=2, sort_keys=True))
    return 0


def cmd_mart_bootstrap(args: argparse.Namespace) -> int:
    """Run one controlled zero-Maximo local Mart bootstrap."""
    from src.services.local_mart_projector import bootstrap_local_mart

    registry_file = args.registry_file or os.environ.get("MAXIMO_ASSET_REGISTRY_FILE")
    if not registry_file:
        print(json.dumps({"status": "BLOCKED", "reason": "REGISTRY_FILE_REQUIRED"}, sort_keys=True))
        return 2
    try:
        result = bootstrap_local_mart(
            registry_file,
            get_database(),
            _local_mart_database(),
            expected_sha256=args.expected_sha256,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": type(error).__name__}, sort_keys=True))
        return 2
    print(json.dumps({"status": "DRY_RUN" if args.dry_run else "COMPLETE", **result}, indent=2, sort_keys=True))
    return 0


def cmd_collect_asset_references(args: argparse.Namespace) -> int:
    from src.services.asset_references import collect_asset_references
    from src.repositories.asset_references import AssetReferenceStore
    store = CollectorStore(get_database())
    if args.report_only:
        print(json.dumps(AssetReferenceStore(store._db).coverage(), indent=2))
        return 0
    service, _ = _sync_service(store)
    result = collect_asset_references(service._client, store, limit=args.limit,
        scheduled=False, max_seconds=args.max_seconds)
    print(json.dumps(result, sort_keys=True))
    return 2 if result["errors"] else 0


def cmd_collect_asset_inventory_batch(args):
    from src.services.asset_inventory import read_role_reference
    from src.services.asset_inventory_sweep import collect_sweep_batch
    from src.repositories.asset_inventory import AssetInventoryStore
    from src.repositories.asset_inventory_sweep import SweepStore
    reference=read_role_reference(args.workbook)
    store=CollectorStore(get_database())
    AssetInventoryStore(store._db).create_tables();SweepStore(store._db).create_tables()
    result=collect_sweep_batch(_sync_service(store)[0]._client,store,reference,
        identity=args.sweep_id,new=args.new_sweep,max_requests=args.max_requests,max_seconds=args.max_seconds,page_size=args.page_size)
    print(json.dumps(result,sort_keys=True))
    return 2 if result.get("errors") else 0


def cmd_refresh_asset_inventory(args):
    from src.services.asset_inventory import read_role_reference, refresh_inventory
    from src.repositories.asset_inventory import AssetInventoryStore
    reference = read_role_reference(args.workbook)
    store = CollectorStore(get_database())
    AssetInventoryStore(store._db).create_tables()
    client = None if args.local_only else _sync_service(store)[0]._client
    result = refresh_inventory(store, reference, client=client,
        max_requests=args.max_requests, max_seconds=args.max_seconds, page_size=args.page_size)
    print(json.dumps(result, sort_keys=True))
    return 2 if result["errors"] else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="mxcollector", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    batch=sub.add_parser("collect-asset-inventory-batch",help="manual resumable 50-row assetid sweep and verification")
    batch.add_argument("--workbook",required=True)
    selection=batch.add_mutually_exclusive_group()
    selection.add_argument("--sweep-id")
    selection.add_argument("--new-sweep",action="store_true")
    batch.add_argument("--max-requests",type=int,default=40)
    batch.add_argument("--max-seconds",type=int,default=150)
    batch.add_argument("--page-size",type=int,choices=(10,25,50),default=50)
    inv = sub.add_parser("refresh-asset-inventory", help="manual BSR hierarchy inventory, never scheduled")
    inv.add_argument("--workbook", required=True)
    inv.add_argument("--local-only", action="store_true")
    inv.add_argument("--max-requests", type=int, default=50)
    inv.add_argument("--max-seconds", type=int, default=180)
    inv.add_argument("--page-size", type=int, choices=(25, 50, 100), default=50)
    sub.add_parser("init-db", help="create collector local tables")
    asset_refs = sub.add_parser("collect-asset-references", help="bounded exact-ID enrichment of missing WO assets")
    asset_refs.add_argument("--limit", type=int, choices=range(1, 51), default=10)
    asset_refs.add_argument("--max-seconds", type=int, choices=range(1, 181), default=45)
    asset_refs.add_argument("--report-only", action="store_true")

    sync = sub.add_parser(
        "sync",
        help="sync operational objects (asset refresh requires explicit mxapiasset)",
    )
    sync.add_argument("objects", nargs="*", help=f"any of: {', '.join(AVAILABLE_OBJECTS)} (or aliases)")

    bootstrap = sub.add_parser("bootstrap-workorders-recent",
        help="explicit bounded recovery to a durable local WO floor; establishes cursor only after reconciliation")
    bootstrap.add_argument("--page-size", type=_bootstrap_limit(25), default=25)
    bootstrap.add_argument("--max-pages", type=_bootstrap_limit(1000), required=True)
    bootstrap.add_argument("--request-budget", type=_bootstrap_limit(2000), required=True)

    backfill = sub.add_parser(
        "backfill",
        help="complete a cursor-independent, read-only BSR work-order traversal",
    )
    backfill.add_argument("--page-size", type=int, default=100)
    backfill.add_argument("--max-pages", type=int, default=1000)

    repair = sub.add_parser(
        "repair-asset-coverage",
        help="run one bounded current MXAPIASSET baseline and reconcile the registry",
    )
    repair.add_argument(
        "--registry-file",
        help="local HTML-export .xls path; defaults to MAXIMO_ASSET_REGISTRY_FILE",
    )
    repair.add_argument("--page-size", type=int, default=50, choices=range(1, 101))
    repair.add_argument("--max-pages", type=int, default=200, choices=range(1, 201))
    # Keep the conservative default; the small explicit upper bound supports
    # the MX-011C continuation without introducing an unbounded mode.
    repair.add_argument("--request-budget", type=int, default=150, choices=range(1, 221))
    repair.add_argument("--dry-run", action="store_true", help="probe and report without Collector writes or cursor changes")

    residual = sub.add_parser(
        "repair-asset-registry-residuals",
        help="complete only current registry Assets missing from local Equipment",
    )
    residual.add_argument(
        "--registry-file",
        help="local HTML-export .xls path; defaults to MAXIMO_ASSET_REGISTRY_FILE",
    )
    residual.add_argument(
        "--dry-run",
        action="store_true",
        help="verify exact residual source rows without Collector writes",
    )

    run = sub.add_parser("run", help="run scheduled, read-only operational and asset sync loops")
    run.add_argument("--operational-interval-seconds", type=int, default=300)
    run.add_argument("--asset-interval-seconds", type=int, default=21600)

    serve = sub.add_parser("serve", help="start the FastAPI app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8002)

    diagnose = sub.add_parser("diagnose", help="run read-only Maximo diagnostics")
    diagnose_sub = diagnose.add_subparsers(dest="diagnose_target", required=True)
    diagnose_sub.add_parser("master-data", help="probe Persons, Items, and Labor scopes")

    profile = sub.add_parser(
        "profile-workorders",
        help="profile bounded, read-only MXWODETAIL population slices",
    )
    profile.add_argument(
        "--mode",
        choices=("default-source", "recent-source", "compare"),
        default="compare",
    )
    profile.add_argument("--source-cap", type=int, default=500, choices=range(1, 501))
    profile.add_argument("--page-size", type=int, default=25, choices=range(1, 26))
    profile.add_argument("--max-pages", type=int, default=20, choices=range(1, 21))
    profile.add_argument("--request-budget", type=int, default=30, choices=range(1, 31))

    reconcile = sub.add_parser(
        "reconcile-asset-registry",
        help="reconcile a local HTML List of Assets export with Collector hierarchy",
    )
    reconcile.add_argument(
        "--registry-file",
        help="local HTML-export .xls path; defaults to MAXIMO_ASSET_REGISTRY_FILE",
    )
    reconcile.add_argument(
        "--verify-missing",
        action="store_true",
        help="perform one bounded GET-only sample against MXAPIASSET and MXASSET",
    )
    reconcile.add_argument("--sample-size", type=int, default=10, choices=range(1, 11))

    mart_load = sub.add_parser(
        "mart-load",
        help="run the bounded initial-controlled Reliability Mart load",
    )
    mart_load.add_argument("--profile", choices=("initial-controlled",), default="initial-controlled")
    mart_load.add_argument("--dry-run", action="store_true", help="map and validate without Mart writes")
    mart_load.add_argument("--entity", help="one allowlisted source alias for a controlled retry")
    mart_load.add_argument("--record-cap", type=int, help="bounded source-record override for --entity")

    registry_import = sub.add_parser(
        "mart-import-asset-registry",
        help="LOCAL ONLY: activate a validated List of Assets registry snapshot",
    )
    registry_import.add_argument("--registry-file", help="external HTML-export .xls path")
    registry_import.add_argument("--expected-sha256", help="optional one-time migration fingerprint check")
    registry_import.add_argument("--dry-run", action="store_true")

    mart_project = sub.add_parser(
        "mart-project",
        help="LOCAL ONLY: project Collector Equipment and Work Orders into the Mart",
    )
    mode = mart_project.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true", help="scan all local rows (default)")
    mode.add_argument("--incremental", action="store_true", help="use local projection watermark with overlap")
    mart_project.add_argument("--batch-size", type=int, default=500, choices=range(1, 5001))

    bootstrap = sub.add_parser(
        "mart-bootstrap",
        help="LOCAL ONLY: project Collector data and activate the current registry",
    )
    bootstrap.add_argument("--registry-file", help="external HTML-export .xls path")
    bootstrap.add_argument("--expected-sha256", required=True, help="one-time current snapshot fingerprint")
    bootstrap.add_argument("--batch-size", type=int, default=500, choices=range(1, 5001))
    bootstrap.add_argument("--dry-run", action="store_true")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    if args.command == "collect-asset-inventory-batch":
        return cmd_collect_asset_inventory_batch(args)
    if args.command == "refresh-asset-inventory":
        return cmd_refresh_asset_inventory(args)
    if args.command == "collect-asset-references":
        return cmd_collect_asset_references(args)
    if args.command == "init-db":
        return cmd_init_db(args)
    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "bootstrap-workorders-recent":
        return cmd_bootstrap_workorders_recent(args)
    if args.command == "backfill":
        return cmd_backfill(args)
    if args.command == "repair-asset-coverage":
        return cmd_repair_asset_coverage(args)
    if args.command == "repair-asset-registry-residuals":
        return cmd_repair_asset_registry_residuals(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "serve":
        return cmd_serve(args)
    if args.command == "diagnose" and args.diagnose_target == "master-data":
        return cmd_diagnose(args)
    if args.command == "profile-workorders":
        return cmd_profile_workorders(args)
    if args.command == "reconcile-asset-registry":
        return cmd_reconcile_asset_registry(args)
    if args.command == "mart-load":
        return cmd_mart_load(args)
    if args.command == "mart-import-asset-registry":
        return cmd_mart_import_asset_registry(args)
    if args.command == "mart-project":
        return cmd_mart_project(args)
    if args.command == "mart-bootstrap":
        return cmd_mart_bootstrap(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())

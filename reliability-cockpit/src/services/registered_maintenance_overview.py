"""Read-only registered Asset/WO summaries, separate from persistence contracts."""
from datetime import datetime, timezone
from sqlalchemy import asc, desc, func, select
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import SITE_CODE, ORGANIZATION_CODE


def registered_maintenance_overview(database) -> dict[str, object]:
    """All retained Registry BSR/IP WO totals, without unrelated domain queries.

    Aggregation is in SQL after both scope predicates and the Registry join.
    The top ten table is explicitly an activity ranking, not the Asset Register.
    """
    scope = (
        select(MaintenanceEventMart.equipment_id, MaintenanceEventMart.canonical_id,
               MaintenanceEventMart.actual_start, MaintenanceEventMart.source_changed_at)
        .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id)
        .where(MaintenanceEventMart.site_code == SITE_CODE,
               MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
               ReliabilityAssetRegistryMart.site_code == SITE_CODE,
               ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE)
    ).subquery()
    count = func.count(scope.c.canonical_id)
    latest = func.max(func.coalesce(scope.c.actual_start, scope.c.source_changed_at))
    ranking = (
        select(ReliabilityAssetRegistryMart.asset_ref, ReliabilityAssetRegistryMart.source_asset_number,
               AssetMasterMart.description, count.label("event_count"), latest.label("latest_activity"))
        .select_from(scope)
        .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == scope.c.equipment_id)
        .outerjoin(AssetMasterMart, (AssetMasterMart.canonical_id == scope.c.equipment_id)
                   & (AssetMasterMart.site_code == SITE_CODE) & (AssetMasterMart.organization_code == ORGANIZATION_CODE))
        .group_by(ReliabilityAssetRegistryMart.asset_ref, ReliabilityAssetRegistryMart.source_asset_number, AssetMasterMart.description)
        .order_by(desc(count), asc(ReliabilityAssetRegistryMart.asset_ref)).limit(10)
    )
    with database.read_session() as session:
        totals = session.execute(select(count, func.count(func.distinct(scope.c.equipment_id)))).one()
        registered = session.scalar(select(func.count(ReliabilityAssetRegistryMart.asset_ref)).where(
            ReliabilityAssetRegistryMart.site_code == SITE_CODE, ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE))
        rows = session.execute(ranking).all()
    return {
        "scope": {"site_code": SITE_CODE, "organization_code": ORGANIZATION_CODE, "kind": "REGISTERED_BSR_IP"},
        "as_of": datetime.now(timezone.utc),
        "summary": {"registered_assets": int(registered or 0), "maintenance_events": int(totals[0] or 0), "assets_with_maintenance": int(totals[1] or 0)},
        "assets": [{"canonical_id": r.asset_ref, "source_asset_number": r.source_asset_number,
                    "description": r.description, "maintenance_events": int(r.event_count),
                    "latest_retained_activity": r.latest_activity} for r in rows],
        "restricted_sections": ["FMEA_HEALTH_PI", "RCFA_OVERHAUL", "CROSS_INSPECTION_TRENDS"],
        "operational_kpis": "NOT_ELIGIBLE",
    }


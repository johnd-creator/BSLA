"""Bounded, SELECT-only traversal of retained Maximo parent relationships.

Registry membership and technical hierarchy context are deliberately separate.
No source request, mapping inference, population claim or write is performed.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import exists, func, select

from src.repositories.mart_models import AssetMasterMart as Asset, ReliabilityAssetRegistryMart as Registry

MAX_DEPTH = 32
REF = re.compile(r"asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}\Z")


class HierarchyNode(BaseModel):
    canonical_id: str
    source_asset_number: str | None
    description: str | None
    description_shortened: bool
    parent_asset_ref: str | None
    status: str | None
    asset_type: str | None
    unit: str | None
    registered: bool
    hierarchy_role: Literal["UNKNOWN"] = "UNKNOWN"
    source_has_children: bool | None
    source_updated_at: datetime | None


class HierarchyView(BaseModel):
    root_ref: str
    node: HierarchyNode
    node_relation: Literal["ROOT", "DESCENDANT", "ANCESTOR"] = "ROOT"
    path: list[HierarchyNode]
    ancestors: list[HierarchyNode]
    ancestor_state: Literal["NO_RETAINED_PARENT", "UNRESOLVED_PARENT", "OUT_OF_SCOPE_PARENT", "CYCLE", "DEPTH_LIMIT"]
    unresolved_parent_ref: str | None
    items: list[HierarchyNode]
    total: int
    offset: int
    limit: int
    has_more: bool
    completeness: Literal["PARTIAL"] = "PARTIAL"
    source: Literal["RETAINED_MAXIMO_PARENT"] = "RETAINED_MAXIMO_PARENT"
    depth_limit: int = MAX_DEPTH


def _scope():
    return Asset.site_code == "BSR", Asset.organization_code == "IP"


def _registered():
    return exists(select(Registry.asset_ref).where(
        Registry.asset_ref == Asset.canonical_id,
        Registry.site_code == "BSR", Registry.organization_code == "IP",
    ))


def _query():
    # Do not select provenance or unrelated vendor namespaces. Read the Maximo
    # namespace to distinguish a JSON boolean from numeric/string lookalikes;
    # only that bool is projected into the public DTO.
    return select(Asset.canonical_id, Asset.source_asset_number, Asset.description,
        Asset.parent_asset_ref, Asset.status, Asset.asset_type, Asset.unit,
        Asset.source_updated_at, Asset.sources["maximo"].label("maximo_source"),
        _registered().label("registered")).where(*_scope())


def _node(row) -> HierarchyNode:
    children = row.maximo_source.get("children") if isinstance(row.maximo_source, dict) else None
    description = row.description
    parent = row.parent_asset_ref
    return HierarchyNode(
        canonical_id=row.canonical_id, source_asset_number=row.source_asset_number,
        description=description[:1000] if description else description,
        description_shortened=bool(description and len(description) > 1000),
        parent_asset_ref=parent if parent and REF.fullmatch(parent) else None,
        status=row.status, asset_type=row.asset_type, unit=row.unit,
        registered=bool(row.registered), source_has_children=children if type(children) is bool else None,
        source_updated_at=row.source_updated_at,
    )


def read_hierarchy(database, root_ref: str, *, node_ref: str | None = None, offset: int = 0, limit: int = 25) -> HierarchyView | None:
    """Caller admits an exact registered root before requesting technical context.

    A node must be a proven descendant or retained ancestor of that root. Ancestor
    pages expose only the proven branch towards the root, never siblings or other
    descendant branches. Membership proof precedes all child counts and pages.
    """
    node_ref = root_ref if node_ref is None else node_ref
    if not REF.fullmatch(root_ref) or not REF.fullmatch(node_ref):
        return None
    if type(offset) is not int or not 0 <= offset <= 10000 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("HIERARCHY_PAGE_INVALID")
    with database.read_session() as session:
        root = session.execute(_query().where(Asset.canonical_id == root_ref, _registered())).first()
        if root is None:
            return None
        # Ancestors are admitted only by exact retained links from the registered root.
        # Keep closest-first internally, then render oldest-first in the DTO.
        ancestors = []
        seen = {root_ref}
        cursor = root.parent_asset_ref
        state = "NO_RETAINED_PARENT"
        unresolved = None
        for _ in range(MAX_DEPTH):
            if not cursor:
                break
            if not REF.fullmatch(cursor):
                state = "OUT_OF_SCOPE_PARENT"
                break
            if cursor in seen:
                state, unresolved = "CYCLE", cursor
                break
            seen.add(cursor)
            row = session.execute(_query().where(Asset.canonical_id == cursor)).first()
            if row is None:
                state, unresolved = "UNRESOLVED_PARENT", cursor
                break
            ancestors.append(_node(row))
            cursor = row.parent_asset_ref
        else:
            if cursor:
                state = "DEPTH_LIMIT"

        ancestor_index = next((i for i, node in enumerate(ancestors) if node.canonical_id == node_ref), None)
        if ancestor_index is not None:
            # Selecting a parent is context navigation, not permission to enumerate
            # every child of that parent. The only item is the already-proven edge.
            branch = _node(root) if ancestor_index == 0 else ancestors[ancestor_index - 1]
            node = ancestors[ancestor_index]
            path = list(reversed(ancestors[:ancestor_index + 1])) + [_node(root)]
            items = [branch] if offset == 0 else []
            total, relation = 1, "ANCESTOR"
        else:
            path = []
            seen = set()
            cursor = node_ref
            for _ in range(MAX_DEPTH):
                if cursor in seen or not REF.fullmatch(cursor):
                    return None
                seen.add(cursor)
                row = root if cursor == root_ref else session.execute(_query().where(Asset.canonical_id == cursor)).first()
                if row is None:
                    return None
                path.append(_node(row))
                if cursor == root_ref:
                    break
                cursor = row.parent_asset_ref or ""
            else:
                if cursor != root_ref:
                    return None
                path.append(_node(root))
            path.reverse()
            node = path[-1]
            relation = "ROOT" if node_ref == root_ref else "DESCENDANT"
            children = (*_scope(), Asset.parent_asset_ref == node_ref,
                        Asset.canonical_id.like("asset:MAXIMO:MXASSET:BSR:IP:%"))
            total = session.scalar(select(func.count()).select_from(Asset).where(*children)) or 0
            rows = session.execute(_query().where(*children).order_by(Asset.canonical_id).offset(offset).limit(limit)).all()
            if any(not REF.fullmatch(row.canonical_id) for row in rows):
                raise ValueError("HIERARCHY_SOURCE_IDENTIFIER_INVALID")
            items = [_node(row) for row in rows]
        return HierarchyView(root_ref=root_ref, node=node, node_relation=relation,
            path=path, ancestors=list(reversed(ancestors)), ancestor_state=state,
            unresolved_parent_ref=unresolved, items=items, total=total, offset=offset,
            limit=limit, has_more=offset + len(items) < total)

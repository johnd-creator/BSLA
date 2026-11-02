"use client";

import { idText, errorLabel, statusLabel } from "../../../lib/id-copy";
import Link from "next/link";
import { useEffect, useState } from "react";
import { reliabilityApi, type AssetFilters, type AssetView, type Page } from "../../../lib/api";
import {assetDetailHref} from "../../../lib/asset-evidence";
import { formatDate } from "../../../lib/format";
import { EmptyState, ErrorState, Identifier, LoadingState, PageHeader, Pagination, SectionCard, StatusBadge, StatCard, TableFrame, SearchField, Button } from "../../../components/ui";

const LIMIT = 50;

export default function AssetsPage() {
  const [page, setPage] = useState<Page<AssetView> | null>(null);
  const [filters, setFilters] = useState<AssetFilters>({ limit: LIMIT });
  const [draft, setDraft] = useState({ status: "", unit: "", asset_type: "" });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [ready, setReady] = useState(false);
  useEffect(() => {
    const read = () => {const q = new URLSearchParams(location.search), offset = Number(q.get('offset') ?? 0);
      const next = {status:q.get('status') ?? '',unit:q.get('unit') ?? '',asset_type:q.get('asset_type') ?? ''};
      setDraft(next); setSearch(q.get('search') ?? '');
      setFilters({...next,limit:LIMIT,offset:Number.isSafeInteger(offset)&&offset>=0&&offset<=1000000?offset:0}); setReady(true);};
    read(); window.addEventListener('popstate',read); return () => window.removeEventListener('popstate',read);
  }, []);
  function navigate(next: AssetFilters, nextSearch = search) {const q = new URLSearchParams();
    for (const key of ['status','unit','asset_type','offset'] as const) if (next[key]) q.set(key,String(next[key]));
    if (nextSearch) q.set('search',nextSearch); history.pushState({},'',`/assets${q.size?'?'+q:''}`); setFilters(next);
  }
  function detailHref(id: string) {const q = new URLSearchParams(); for (const key of ['status','unit','asset_type','offset'] as const) if(filters[key])q.set(key,String(filters[key])); if(search)q.set('search',search);return assetDetailHref(id,q);}
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    setLoading(true);
    reliabilityApi.assets(filters).then((next) => { if (!cancelled) { setPage(next); setError(null); } }).catch((reason: unknown) => { if (!cancelled) setError(reason instanceof Error ? errorLabel(reason) : idText("Reliability Mart unavailable")); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters, refresh, ready]);

  const visible = page?.items.filter(asset => [asset.canonical_id, asset.source_asset_number, asset.description, asset.location_ref].some(value => value?.toLowerCase().includes(search.trim().toLowerCase()))) ?? [];

  function applyFilters() { navigate({ status: draft.status || undefined, unit: draft.unit || undefined, asset_type: draft.asset_type || undefined, limit: LIMIT, offset: 0 }); }
  function changePage(offset: number) { navigate({ ...filters, offset }); }

  return <>
    <PageHeader eyebrow={idText("Registered Asset projection")} title={idText("Asset Register")} description={idText("Registered Reliability Assets dari snapshot List of Assets, diperkaya konteks teknis lokal tanpa mengunduh seluruh records.")} actions={<span className="scope-chip">BSR / IP</span>} />
    <section className="stat-grid asset-register-stats"><StatCard label={idText("Registered assets")} value={!loading && !error && page ? page.meta.total : "UNKNOWN"} detail={idText("Server-filtered Registry population")} /><StatCard label={idText("Health score")} value="NOT ASSESSED" detail={idText("No approved numerical assessment")} /><StatCard label={idText("Evidence scope")} value="BSR / IP" detail={idText("Technical equipment remains separate")} /></section>
    <SectionCard className="filter-card"><div className="filter-heading"><div><p className="eyebrow">{idText("Asset filters")}</p><strong>{idText("Find a registered asset")}</strong></div><span className="muted-label">{idText("Server filters · 50 rows; search this page only")}</span></div><div className="filter-grid"><SearchField id="asset-page-search" label={idText("Search this page")} value={search} onChange={e => setSearch(e.target.value)} placeholder={idText("Identity, description or location")} /><label>Status<input value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })} placeholder={idText("e.g. ACTIVE")} /></label><label>{idText("Unit")}<input value={draft.unit} onChange={(event) => setDraft({ ...draft, unit: event.target.value })} placeholder={idText("e.g. Unit 1")} /></label><label>{idText("Asset type")}<input value={draft.asset_type} onChange={(event) => setDraft({ ...draft, asset_type: event.target.value })} placeholder={idText("e.g. PRODUCTION")} /></label></div><div className="engineering-actions"><Button variant="primary" onClick={applyFilters}>{idText("Apply filters")}</Button><Button onClick={() => {setDraft({status:"",unit:"",asset_type:""});setSearch("");navigate({limit:LIMIT}, "");}}>{idText("Clear filters")}</Button></div></SectionCard>
    <SectionCard className="data-section"><div className="section-heading"><div><p className="eyebrow">{idText("Reliability Mart / Registered Assets")}</p><h2>{!loading && !error && page ? page.meta.total.toLocaleString("id-ID") : statusLabel("UNKNOWN")}  {idText("registered assets")}</h2></div>{page && <span className="dataset-badge compact">{idText("Current registry projection")}</span>}</div>
      {loading && <LoadingState />}{!loading && error && <ErrorState message={idText("Asset Register unavailable")} onRetry={() => setRefresh(value => value + 1)} />}{!loading && !error && page && visible.length === 0 && <EmptyState title={idText("No registered assets match these page filters.")} detail={idText("Page search covers only the loaded server page; no condition conclusion follows.")} />}{!loading && !error && page && visible.length > 0 && <><TableFrame minWidth={1120}><table><thead><tr><th>{idText("Asset")}</th><th>{idText("Description")}</th><th>{idText("Source Status")}</th><th>{idText("Location")}</th><th>{idText("Type")}</th><th>{idText("Plant")}</th><th>{idText("Unit")}</th><th>{idText("Source record updated")}</th><th>{idText("Assessment")}</th><th>{idText("Open")}</th></tr></thead><tbody>{visible.map((asset) => <tr key={asset.canonical_id}><td><strong><Link className="asset-row-link" href={detailHref(asset.canonical_id)}>{asset.source_asset_number ?? <Identifier value={asset.canonical_id} />}</Link></strong><small className="table-subtext"><Identifier value={asset.canonical_id} /></small></td><td className="wide-cell">{asset.description ?? "—"}</td><td><StatusBadge value={asset.status} mode="raw-neutral" /></td><td>{asset.location_ref ?? "—"}</td><td>{asset.asset_type ?? "—"}</td><td>{asset.plant ?? "—"}</td><td>{asset.unit ?? "—"}</td><td>{formatDate(asset.source_updated_at)}<small className="table-subtext">{idText("Record timestamp, not freshness")}</small></td><td>{statusLabel("NOT ASSESSED")}<small className="table-subtext">{idText("See asset evidence")}</small></td><td><Link className="table-action" href={detailHref(asset.canonical_id)}>{idText("View Asset →")}</Link></td></tr>)}</tbody></table></TableFrame><Pagination meta={page.meta} onChange={changePage} /></>}</SectionCard>
  </>;
}

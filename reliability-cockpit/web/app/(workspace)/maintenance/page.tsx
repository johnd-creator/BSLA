"use client";

import { idText, errorLabel } from "../../../lib/id-copy";
import Link from "next/link";
import { useEffect, useState } from "react";
import { reliabilityApi, type MaintenanceEventView, type MaintenanceFilters, type Page } from "../../../lib/api";
import { formatNumber } from "../../../lib/format";
import { woDate } from "../../../lib/wo-date";
import { EmptyState, ErrorState, Identifier, LoadingState, PageHeader, Pagination, SectionCard, StatusBadge, TableFrame } from "../../../components/ui";

const LIMIT = 50;

export default function MaintenancePage() {
  const [page, setPage] = useState<Page<MaintenanceEventView> | null>(null);
  const [filters, setFilters] = useState<MaintenanceFilters>({ limit: LIMIT });
  const [draft, setDraft] = useState({ status: "", event_type: "", work_order_id: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    reliabilityApi.maintenance(filters).then((next) => { if (!cancelled) { setPage(next); setError(null); } }).catch((reason: unknown) => { if (!cancelled) setError(reason instanceof Error ? errorLabel(reason) : idText("Reliability Mart unavailable")); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters]);

  function applyFilters() { setFilters({ status: draft.status || undefined, event_type: draft.event_type || undefined, work_order_id: draft.work_order_id || undefined, limit: LIMIT, offset: 0 }); }
  return <>
    <PageHeader eyebrow={idText("Registered Asset workspace")} title={idText("Maintenance")} description={idText("Work Order history yang diproyeksikan lokal dari Collector dan dibatasi ke Registered Reliability Assets.")} actions={<div className="overview-actions"><span className="scope-chip">BSR / IP</span><Link className="button primary" href="/maintenance/investigation">{idText("Open Maintenance Investigation →")}</Link></div>} />
    <SectionCard className="filter-card"><div className="filter-heading"><div><p className="eyebrow">{idText("Event filters")}</p><strong>{idText("Search the maintenance event page")}</strong></div><span className="muted-label">{idText("Server-side · 50 rows")}</span></div><div className="filter-grid"><label>Status<input value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })} placeholder={idText("e.g. COMPLETE")} /></label><label>{idText("Work Type")}<input value={draft.event_type} onChange={(event) => setDraft({ ...draft, event_type: event.target.value })} placeholder={idText("e.g. PM")} /></label><label>Work Order<input value={draft.work_order_id} onChange={(event) => setDraft({ ...draft, work_order_id: event.target.value })} placeholder={idText("Reference")} /></label><button className="button primary" type="button" onClick={applyFilters}>{idText("Apply filters")}</button></div></SectionCard>
    <p className="section-note">Terakhir Diubah di Maximo adalah perubahan rekam sumber, bukan waktu pelaksanaan pekerjaan. Tanggal aktual yang kosong tetap BELUM TERSEDIA.</p><SectionCard className="data-section"><div className="section-heading"><div><p className="eyebrow">{idText("Reliability Mart / Registered Assets")}</p><h2>{page?.meta.total.toLocaleString("id-ID") ?? "—"}  {idText("maintenance events")}</h2></div>{page && <span className="dataset-badge compact">{idText("Local Collector projection")}</span>}</div>
      {loading && <LoadingState />}{!loading && error && <ErrorState message={error} />}{!loading && !error && page && page.items.length === 0 && <EmptyState />}{!loading && !error && page && page.items.length > 0 && <><TableFrame minWidth={1100}><table><thead><tr><th>Work Order</th><th>{idText("Asset")}</th><th>{idText("Work Type")}</th><th>{idText("Source Status")}</th><th>Mulai aktual</th><th>{idText("Actual finish")}</th><th>Terakhir Diubah di Maximo</th><th>{idText("Downtime")}</th><th>{idText("Labor hours")}</th></tr></thead><tbody>{page.items.map((row) => <tr key={row.canonical_id}><td><Identifier value={row.work_order_id ?? row.id} /></td><td><Identifier value={row.equipment_id} /></td><td>{row.event_type ?? "UNKNOWN"}</td><td><StatusBadge value={row.status} mode="raw-neutral" /></td><td>{woDate(row.actual_start)}</td><td>{woDate(row.actual_finish)}</td><td>{woDate(row.source_changed_at)}</td><td>{formatNumber(row.downtime_hours)} h</td><td>{formatNumber(row.labor_hours)} h</td></tr>)}</tbody></table></TableFrame><Pagination meta={page.meta} onChange={(offset) => setFilters((current) => ({ ...current, offset }))} /></>}</SectionCard>
  </>;
}

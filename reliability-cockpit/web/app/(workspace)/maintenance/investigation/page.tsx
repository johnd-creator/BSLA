"use client";

import { idText, errorLabel } from "../../../../lib/id-copy";
import Link from "next/link";
import { useEffect, useState } from "react";
import { reliabilityApi, type MaintenanceInvestigationView } from "../../../../lib/api";
import { formatNumber } from "../../../../lib/format";
import { woDate } from "../../../../lib/wo-date";
import { DataMaturity, EmptyState, ErrorState, LoadingState, PageHeader, Pagination, SectionCard, StatCard, TableFrame } from "../../../../components/ui";

const WINDOWS = [30, 90, 180] as const;
const MIN_EVENTS = [2, 3, 5] as const;
type WindowDays = (typeof WINDOWS)[number];
type MinEvents = (typeof MIN_EVENTS)[number];
type SortMode = "event_count_desc" | "latest_activity_desc" | "latest_gap_asc";

export default function MaintenanceInvestigationPage() {
  const [windowDays, setWindowDays] = useState<WindowDays>(90);
  const [minEvents, setMinEvents] = useState<MinEvents>(2);
  const [sort, setSort] = useState<SortMode>("event_count_desc");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<MaintenanceInvestigationView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    reliabilityApi.maintenanceInvestigation(windowDays, minEvents, offset, 25, sort).then((next) => {
      if (!cancelled) { setData(next); setError(null); }
    }).catch((reason: unknown) => {
      if (!cancelled) setError(reason instanceof Error ? errorLabel(reason) : idText("Reliability Mart unavailable"));
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [windowDays, minEvents, offset, sort]);

  function changeWindow(value: WindowDays) { setWindowDays(value); setOffset(0); }
  function changeMinEvents(value: MinEvents) { setMinEvents(value); setOffset(0); }
  function changeSort(value: SortMode) { setSort(value); setOffset(0); }

  return <>
    <PageHeader
      eyebrow={idText("Maintenance / Investigation")}
      title={idText("Maintenance Investigation")}
      description="Menelusuri pola aktivitas Maintenance berulang pada Registered Reliability Assets tanpa mengasumsikan kegagalan atau risiko."
      actions={<div className="overview-actions"><span className="scope-chip">BSR / IP</span><Link className="button" href="/maintenance">{idText("Back to Maintenance")}</Link></div>}
    />
    <div className="scope-banner trust-strip"><DataMaturity state="CURRENT LOCAL PROJECTION" detail={idText("Maintenance data are projected locally from Collector into the Mart.")} /><span>{idText("Registry-scoped Maintenance")}</span><span className="muted-label">{data?.evidence.work_type_source ?? idText("Source Work Type → fallback → UNKNOWN")}</span></div>
    <SectionCard className="neutral-note"><strong>Aktivitas berulang berarti lebih dari satu catatan WO pada aset yang sama dalam periode ini. Bukan bukti pekerjaan fisik atau gangguan berulang.</strong></SectionCard>
    <SectionCard className="filter-card"><div className="filter-heading"><div><p className="eyebrow">{idText("Investigation window")}</p><strong>{idText("Bounded activity sequence")}</strong></div><span className="muted-label">Tanggal referensi memakai actual start atau perubahan catatan, bukan bukti aktivitas fisik harian.</span></div><div className="filter-grid compact-filter"><label>{idText("Current data window")}<select value={windowDays} onChange={(event) => changeWindow(Number(event.target.value) as WindowDays)}>{WINDOWS.map(days=><option key={days} value={days}>{days} hari</option>)}</select></label><label>{idText("Minimum events")}<select value={minEvents} onChange={(event) => changeMinEvents(Number(event.target.value) as MinEvents)}>{MIN_EVENTS.map(count=><option key={count} value={count}>{count}+ kejadian</option>)}</select></label><label>{idText("Sort")}<select value={sort} onChange={(event) => changeSort(event.target.value as SortMode)}><option value="event_count_desc">{idText("Event count, high to low")}</option><option value="latest_activity_desc">{idText("Latest activity, newest")}</option><option value="latest_gap_asc">{idText("Latest gap, shortest")}</option></select></label></div></SectionCard>
    {loading && <LoadingState label={idText("Reading bounded Maintenance Investigation aggregates…")} />}
    {!loading && error && <ErrorState message={error} />}
    {!loading && !error && data && <>
      <section className="stat-grid investigation-stat-grid"><StatCard label={`Catatan WO ${windowDays} hari`} value={formatNumber(data.summary.maintenance_events)} detail={idText("Registry-scoped · DERIVED_SAFE")} tone="accent" /><StatCard label={idText("Assets with Activity")} value={formatNumber(data.summary.assets_with_activity)} detail={idText("Distinct registered Assets · DERIVED_SAFE")} /><StatCard label={idText("Assets with 2+ Events")} value={formatNumber(data.summary.assets_with_2plus_events)} detail={idText("Repeat Activity candidate · DERIVED_SAFE")} /><StatCard label={idText("Repeat Activity Events")} value={formatNumber(data.summary.repeat_activity_events)} detail={idText("Events beyond the first · DERIVED_SAFE")} /></section>
      <SectionCard className="data-section"><div className="section-heading"><div><p className="eyebrow">{minEvents}{idText("+ events ·")} {windowDays}d</p><h2>{idText("Repeated Maintenance Activity")}</h2></div><span className="muted-label">{data.meta.total.toLocaleString("id-ID")}  {idText("Assets in result · server-side")}</span></div>{data.assets.length === 0 ? <EmptyState title={idText("No Assets meet this activity threshold in the selected window.")} detail={idText("This is an empty activity result, not a reliability conclusion.")} /> : <TableFrame minWidth={1220}><table><thead><tr><th>{idText("Asset")}</th><th>{idText("Description")}</th><th>{idText("Maintenance Events")}</th><th>{idText("Repeat Activity Events")}</th><th>{idText("Latest Activity")}</th><th>{idText("Previous Activity")}</th><th>{idText("Latest Gap")}</th><th>{idText("Latest Work Type")}</th><th>{idText("Dominant Work Type")}</th></tr></thead><tbody>{data.assets.map((asset) => <tr key={asset.asset_ref}><td><Link className="asset-row-link" href={`/assets/${encodeURIComponent(asset.asset_ref)}`}>{asset.source_asset_number}</Link></td><td className="wide-cell">{asset.description ?? "—"}</td><td><strong>{formatNumber(asset.event_count)}</strong></td><td>{formatNumber(asset.repeat_activity_events)}</td><td>{woDate(asset.latest_activity)}</td><td>{woDate(asset.previous_activity)}</td><td>{asset.latest_gap_days == null ? "—" : `${asset.latest_gap_days.toFixed(1)} hari`}</td><td>{asset.latest_work_type ?? "UNKNOWN"}</td><td>{asset.dominant_work_type ?? "UNKNOWN"}</td></tr>)}</tbody></table></TableFrame>}<Pagination meta={data.meta} onChange={setOffset} /></SectionCard>
      <p className="section-note">{data.evidence.activity_date}  {idText("Intervals are descriptive only. Repeated activity can include planned, inspection, administrative, or cancelled source events; raw source statuses remain unchanged.")}</p>
    </>}
  </>;
}

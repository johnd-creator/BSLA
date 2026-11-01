"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, reliabilityApi } from "../lib/api";
import { reportCandidates, reportPeriods, ReportPeriodMismatch, requireReportPeriod, type ReportCandidate, type ReportPeriod } from "../lib/reports";
import ReliabilityPerformance from "./ReliabilityPerformance";
import CoverageReport from "./CoverageReport";
import MaintenanceReport from "./MaintenanceReport";
import { Breadcrumbs, Button, EmptyState, HelpDetails, LoadingState, PageHeader, SectionCard } from "./ui";

function useReport<T>(read: () => Promise<T>) {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: string | null }>({ data: null, loading: true, error: null });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: null });
    read().then(data => { if (active) setState({ data, loading: false, error: null }); }).catch((error: unknown) => {
      if (active) setState({ data: null, loading: false, error: error instanceof ReportPeriodMismatch ? "Periode respons tidak sesuai permintaan. Preview tidak ditampilkan." : error instanceof ApiError && [401,403].includes(error.status) ? "Akses laporan ditolak. Gunakan akses yang berwenang; tidak ada bypass otorisasi." : "API laporan tidak tersedia atau tidak dapat dibaca. Bukti tetap UNKNOWN." });
    });
    return () => { active = false; };
  }, [read, attempt]);
  return { ...state, retry: () => setAttempt(value => value + 1) };
}
function ReportError({ message, retry }: { message: string; retry: () => void }) {
  return <div className="state-card error-state" role="alert"><h3>Preview tidak tersedia</h3><p>{message}</p><Button onClick={retry}>Baca ulang laporan kandidat</Button></div>;
}
function CoverageReader() {
  const state = useReport(reliabilityApi.dataTrust);
  return state.loading ? <LoadingState label="Memuat preview Cakupan Data…" /> : state.error ? <ReportError message={state.error} retry={state.retry} /> : state.data ? <CoverageReport data={state.data} /> : <EmptyState title="Bukti Cakupan Data belum tersedia." />;
}
function MaintenanceReader({ days }: { days: ReportPeriod }) {
  const read = useCallback(() => reliabilityApi.decisionOverview(days).then(data => requireReportPeriod(data, days)), [days]);
  const state = useReport(read);
  return state.loading ? <LoadingState label={`Memuat preview Aktivitas Pemeliharaan ${days} hari…`} /> : state.error ? <ReportError message={state.error} retry={state.retry} /> : state.data ? <MaintenanceReport data={state.data} /> : <EmptyState title="Bukti aktivitas belum tersedia." />;
}
export default function ReportsCenter() {
  const [performance,setPerformance]=useState<boolean|null>(null);
  useEffect(()=>{const read=()=>setPerformance(new URLSearchParams(location.search).get('report_view')==='reliability');read();window.addEventListener('popstate',read);return()=>window.removeEventListener('popstate',read);},[]);
  function selectPerformance(value:boolean){const q=new URLSearchParams(location.search);if(value)q.set('report_view','reliability');else q.delete('report_view');history.pushState({},'','/reports'+(q.size?'?'+q:''));setPerformance(value);}
  const [selected, setSelected] = useState<ReportCandidate["id"]>("coverage");
  const [days, setDays] = useState<ReportPeriod>(30);
  const candidate = reportCandidates.find(value => value.id === selected)!;
  if(performance===null)return <LoadingState label="Memuat konteks laporan…"/>;
  if(performance)return <div className="reports-workspace"><PageHeader eyebrow="NADI / Laporan" title="Kinerja Reliabilitas" description="Definisi dan kesiapan evidence sebelum hasil MTBF/MTTR." actions={<Button onClick={()=>selectPerformance(false)}>Kembali ke katalog laporan</Button>}/><ReliabilityPerformance/></div>;
  return <div className="reports-workspace">
    <Breadcrumbs items={[{ label: "NADI", href: "/" }, { label: "Pusat Laporan" }]} />
    <PageHeader eyebrow="NADI / Preview factual" title="Pusat Laporan" description="Pilih kandidat laporan untuk menelusuri fakta terbatas, lingkup dan ketidakpastiannya." />
    <SectionCard><h2>Kinerja Reliabilitas</h2><p>Periksa prasyarat MTBF/MTTR untuk aset dan periode persis. KPI operasional tetap NOT_ELIGIBLE.</p><Button onClick={()=>selectPerformance(true)}>Buka Kinerja Reliabilitas</Button></SectionCard>
    <div className="scope-banner"><span className="dataset-badge">DEVELOPMENT CANDIDATE — NOT OPERATIONALLY APPROVED</span><span>Definisi kandidat, bukan laporan operasional yang disahkan.</span></div>
    <SectionCard><div className="section-heading"><div><p className="eyebrow">01 / Katalog kandidat</p><h2>Pilih preview laporan</h2></div></div><div className="report-catalog" role="group" aria-label="Katalog laporan kandidat">{reportCandidates.map(item => <button type="button" className={`report-template${selected === item.id ? " selected" : ""}`} key={item.id} aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}><strong>{item.title}</strong><span>{item.name}</span><p>{item.description}</p><small>DEVELOPMENT CANDIDATE — NOT OPERATIONALLY APPROVED</small><span className="report-template-version">{item.definition} · v{item.version}</span></button>)}</div></SectionCard>
    <SectionCard><div className="section-heading"><h2>Lingkup dan kontrol preview</h2>{selected === "maintenance" && <label className="window-select">Periode aktivitas<select aria-label="Periode aktivitas" value={days} onChange={event => { const value = Number(event.target.value); if (reportPeriods.includes(value as ReportPeriod)) setDays(value as ReportPeriod); }}>{reportPeriods.map(value => <option key={value} value={value}>{value} hari</option>)}</select></label>}</div><p>{selected === "coverage" ? "Data Coverage tidak mendukung filter periode. Preview mencakup populasi yang dikembalikan DataTrustView, bukan laporan 30 hari." : "Hanya periode 7, 30 dan 90 hari yang didukung decisionOverview(windowDays). Tidak ada custom range atau pemotongan data di browser."}</p><HelpDetails title="Lingkup sumber & otorisasi"><p>Lingkup sumber existing BSR / IP dan Registry governed; bukan pemilih izin pengguna. Otorisasi deployment masih prasyarat terpisah. Tampilan tidak menambah akses pada endpoint underlying.</p></HelpDetails></SectionCard>
    <section aria-labelledby="report-preview-heading" className="report-preview"><div className="report-preview-heading"><p className="eyebrow">02 / Preview read-only</p><h2 id="report-preview-heading">{candidate.name}</h2><p className="section-note">DEVELOPMENT CANDIDATE — NOT OPERATIONALLY APPROVED · tanpa penyimpanan histori laporan.</p></div>
      {selected === "coverage" ? <CoverageReader key="coverage" /> : <MaintenanceReader key={`maintenance-${days}`} days={days} />}
    </section>
    <SectionCard><div className="section-heading"><h2>Batas penggunaan V1</h2></div><p>Ekspor, unduh file, distribusi, email dan penjadwalan tidak diaktifkan. Tidak ada PDF, XLSX atau CSV operasional yang dibuat. Preview tidak menetapkan KPI, approval engineer atau kesiapan operasi.</p><Link href="/data-quality" className="text-link">Data Trust Center →</Link> · <Link href="/system-integration" className="text-link">Pusat Integrasi Sistem →</Link></SectionCard>
  </div>;
}

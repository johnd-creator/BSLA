"use client";
import {WoEvidenceOverview} from "./WoEvidenceOverview";
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {reliabilityApi} from '../lib/api';
import type {ScopedFactualOverview} from '../lib/factual-read-contract';
import {factualErrorKind,factualErrorMessage} from '../lib/factual-error';
import {woDate} from '../lib/wo-date';
import {Breadcrumbs,ErrorState,LoadingState,PageHeader,SectionCard,StatCard,TableFrame} from './ui';

export default function ScopedExecutiveOverview(){
 const [data,setData]=useState<ScopedFactualOverview|null>(null),[error,setError]=useState<unknown>(null),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let cancelled=false;setLoading(true);setData(null);setError(null);
  reliabilityApi.scopedOverview().then(next=>{if(!cancelled)setData(next);}).catch(reason=>{if(!cancelled)setError(reason);}).finally(()=>{if(!cancelled)setLoading(false);});
  return()=>{cancelled=true;};
 },[retry]);
 return <div className="experience-workspace executive-workspace">
  <Breadcrumbs items={[{label:'NADI'},{label:'Ringkasan Eksekutif'}]} />
  <PageHeader eyebrow="Bukti faktual dalam lingkup izin" title="Ringkasan Eksekutif" description="Aset dan Work Order yang diizinkan untuk akun Anda. Semua akses faktual bersifat baca saja." actions={<Link className="button outline" href="/assets">Buka Aset →</Link>} />
  <section className="overview-filter-bar" aria-label="Lingkup ringkasan"><div><span className="filter-caption">Site / Organisasi</span><strong>BSR / IP</strong></div><div><span className="filter-caption">Populasi</span><strong>{data?.scope.kind==='REGISTERED_BSR_IP'?'Seluruh aset terdaftar BSR/IP':'Hanya aset dalam izin baca Anda'}</strong></div><nav className="engineering-actions" aria-label="Lanjutkan penelusuran"><Link className="button outline" href="/assets">Aset</Link><Link className="button outline" href="/pdm">PdM Center</Link></nav></section>
  {loading&&<LoadingState label="Membaca bukti aset yang diizinkan…" />}
  {!loading&&error!=null&&<ErrorState variant={factualErrorKind(error)} message={factualErrorMessage(error)} onRetry={()=>setRetry(n=>n+1)} />}
  {!loading&&data&&<>
   <WoEvidenceOverview data={data.wo_evidence}/>
   <section className="stat-grid asset-register-stats" aria-label="Ringkasan faktual berizin">
    <StatCard label="Aset terdaftar dalam izin" value={data.summary.registered_assets} detail="Registry BSR / IP · VERIFIED" tone="accent" />
    <StatCard label="WO tersimpan dalam izin" value={data.summary.maintenance_events} detail="Jumlah retained · bukan kelengkapan seluruh riwayat" />
    <StatCard label="Aset dengan WO tersimpan" value={data.summary.assets_with_maintenance} detail="Hanya populasi yang diizinkan · DERIVED_SAFE" />
   </section>
   <SectionCard><div className="section-heading"><h2>{data.scope.kind==='REGISTERED_BSR_IP'?'10 aset dengan WO tersimpan terbanyak':'Aset dan bukti pemeliharaan'}</h2><span className="dataset-badge compact">Baca saja</span></div>
    <p className="section-note">Jumlah dihitung setelah pembatasan scope. Kolom perubahan rekam memakai changedate saja; ini bukan bukti pelaksanaan atau freshness koleksi.</p>
    <TableFrame minWidth={650} label="Aset dalam izin baca"><table><thead><tr><th>Aset</th><th>Deskripsi</th><th>WO tersimpan</th><th>Perubahan rekam terakhir</th><th>Bukti</th></tr></thead><tbody>{data.assets.map(asset=><tr key={asset.canonical_id}>
     <td><Link href={`/assets/${encodeURIComponent(asset.canonical_id)}`}>{asset.source_asset_number??asset.canonical_id}</Link></td><td>{asset.description??'UNKNOWN'}</td><td>{asset.maintenance_events}</td><td><time dateTime={asset.latest_retained_activity??undefined} title={asset.latest_retained_activity??undefined}>{woDate(asset.latest_retained_activity)}</time></td><td><Link href={`/assets/${encodeURIComponent(asset.canonical_id)}?tab=maintenance`}>Maintenance / WO →</Link></td>
    </tr>)}</tbody></table></TableFrame>
    <p className="section-note">Waktu query: <time dateTime={data.as_of} title={data.as_of}>{woDate(data.as_of)}</time>. {data.scope.kind==='REGISTERED_BSR_IP'?'Ringkasan seluruh Registry BSR/IP; tabel menampilkan maksimal 10 aset. Buka Aset untuk daftar lengkap dan pagination.':'Scope ini tidak mewakili keseluruhan pembangkit.'}</p>
   </SectionCard>
  </>}
  <div className="executive-evidence-grid">
   <SectionCard><h2>Bagian dibatasi</h2><p>FMEA, health, PI, RCFA dan overhaul memerlukan izin tersendiri. Tidak ada data bagian tersebut yang dimuat untuk ringkasan ini.</p></SectionCard>
   <SectionCard><h2>Kelayakan analisis</h2><strong>NOT_ELIGIBLE</strong><p>MTBF / MTTR operasional, equipment health dan tren lintas inspeksi menunggu prasyarat serta persetujuan engineering.</p><Link href="/pdm">Lanjutkan alur PdM yang sudah diizinkan →</Link></SectionCard>
  </div>
 </div>;
}

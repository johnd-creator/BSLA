"use client";
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {reliabilityApi,type AssetView} from '../lib/api';
import {evidenceError,evidenceErrorKind} from '../lib/asset-evidence';
import {performanceDefinition,performanceHref,performanceInput,prerequisites} from '../lib/reliability-performance';
import AssetMaintenanceEvidence from './AssetMaintenanceEvidence';
import {Button,EmptyState,ErrorState,LoadingState,SectionCard,TableFrame} from './ui';

type Context={asset:string;start:string;end:string};
const blank:Context={asset:'',start:'',end:''};
export default function ReliabilityPerformance(){
  const [draft,setDraft]=useState<Context>(blank),[selected,setSelected]=useState<Context>(blank),[invalid,setInvalid]=useState<string|null>(null);
  const [state,setState]=useState<{key:string;data:AssetView|null;loading:boolean;error:unknown}>({key:'',data:null,loading:false,error:null});
  const [retry,setRetry]=useState(0),[sourceOpen,setSourceOpen]=useState(false);
  useEffect(()=>{const read=()=>{const q=new URLSearchParams(location.search),next={asset:q.get('rp_asset')??'',start:q.get('rp_start')??'',end:q.get('rp_end')??''};setDraft(next);setSelected(next);setInvalid(next.asset?performanceInput(next.asset,next.start,next.end):null);setSourceOpen(false);};read();window.addEventListener('popstate',read);return()=>window.removeEventListener('popstate',read);},[]);
  useEffect(()=>{
    if(!selected.asset || performanceInput(selected.asset,selected.start,selected.end))return;
    let active=true;setState({key:selected.asset,data:null,loading:true,error:null});
    reliabilityApi.asset(selected.asset).then(asset=>{if(asset.canonical_id!==selected.asset||asset.site_code!=='BSR'||asset.organization_code!=='IP')throw new Error('scope mismatch');if(active)setState({key:selected.asset,data:asset,loading:false,error:null});}).catch(error=>{if(active)setState({key:selected.asset,data:null,loading:false,error});});
    return()=>{active=false;};
  },[selected.asset,selected.start,selected.end,retry]);
  function submit(event:React.FormEvent){event.preventDefault();const next={...draft,asset:draft.asset.trim()};const error=performanceInput(next.asset,next.start,next.end);setInvalid(error);if(error)return;setState({key:next.asset,data:null,loading:true,error:null});setSourceOpen(false);setSelected(next);setRetry(n=>n+1);history.pushState({},'',performanceHref(next.asset,next.start,next.end));}
  const current=state.key===selected.asset&&!invalid&&selected.asset!=='';
  return <div className="reliability-performance asset-evidence">
    <SectionCard><h2>Kinerja Reliabilitas</h2><p>MTBF dan MTTR memerlukan definisi serta evidence yang dikualifikasi. Status operasional: <strong>NOT_ELIGIBLE</strong>.</p><p className="section-note">Rancangan {performanceDefinition} · definisi operasional belum disahkan. Tidak ada mesin kalkulasi yang dipanggil dari halaman ini.</p>
      <form onSubmit={submit}><div className="filter-grid"><label>Referensi aset kanonis<input value={draft.asset} maxLength={200} onChange={event=>setDraft({...draft,asset:event.target.value})} placeholder="Referensi persis dari Aset atau inspeksi" required/></label><label>Awal periode (ISO-8601 + zona)<input value={draft.start} maxLength={80} onChange={event=>setDraft({...draft,start:event.target.value})} placeholder="2026-01-01T00:00:00+07:00" required/></label><label>Akhir periode eksklusif (ISO-8601 + zona)<input value={draft.end} maxLength={80} onChange={event=>setDraft({...draft,end:event.target.value})} placeholder="2026-02-01T00:00:00+07:00" required/></label></div><Button variant="primary" type="submit">Periksa kesiapan evidence</Button></form>
      {invalid&&<ErrorState variant="request" message={invalid}/>}<p className="section-note">Periode pilihan adalah konteks evaluasi yang diminta pengguna, bukan waktu sumber atau persetujuan observasi. Tidak ada calendar-hours fallback.</p>
    </SectionCard>
    {!selected.asset&&!invalid&&<EmptyState title="Pilih aset dan periode untuk membaca kesiapan." detail="Tidak ada KPI atau populasi aset yang diunduh sebelum Anda memilih konteks persis."/>}
    {current&&state.loading&&<LoadingState label="Memeriksa identitas aset melalui akses existing…"/>}
    {current&&!state.loading&&state.error!=null&&<ErrorState message={evidenceError(state.error)} variant={evidenceErrorKind(state.error)} onRetry={()=>setRetry(n=>n+1)}/>}
    {current&&!state.loading&&state.data&&<>
      <SectionCard><h3>{state.data.source_asset_number??state.data.canonical_id}</h3><p>{state.data.description??'Deskripsi tidak tersedia'}</p><dl className="asset-facts"><div><dt>Identitas persis / lingkup</dt><dd>{state.data.canonical_id}<br/>{state.data.site_code} / {state.data.organization_code}</dd></div><div><dt>Periode pilihan [awal, akhir)</dt><dd>{selected.start}<br/>{selected.end}</dd></div></dl><Link className="text-link" href={'/assets/'+encodeURIComponent(selected.asset)}>Buka evidence aset →</Link></SectionCard>
      <section className="performance-metrics" aria-label="Status KPI operasional">{[['MTBF','Qualified operating hours / distinct qualifying failure events'],['MTTR','Qualified active repair hours / completed qualifying repair episodes']].map(([name,definition])=><SectionCard key={name}><h3>{name}</h3><strong>Belum dapat dihitung</strong><p>NOT_ELIGIBLE · satuan kandidat h</p><p>{definition}</p><p className="section-note">Nilai tetap tidak tersedia. Nol, infinity atau KPI proxy legacy tidak dipublikasikan sebagai hasil qualified.</p></SectionCard>)}</section>
      <SectionCard><h3>Eligibility dan data yang masih diperlukan</h3><TableFrame minWidth={900} label="Matriks prasyarat Reliability Performance"><table><thead><tr><th>Prasyarat</th><th>Status</th><th>Owner keputusan</th><th>Alasan / batas evidence</th></tr></thead><tbody>{prerequisites.map(row=><tr key={row.input}><th scope="row">{row.input}</th><td>{row.status}</td><td>{row.owner}</td><td>{row.reason}</td></tr>)}</tbody></table></TableFrame></SectionCard>
      <SectionCard><h3>Failure event / repair episode</h3><p>Dataset qualified tidak tersedia pada kontrak berizin saat ini. Tidak ada event sintetis, diagnosis, health score atau klasifikasi lampu warna yang dimasukkan ke register operasional.</p><details open={sourceOpen} onToggle={event=>setSourceOpen(event.currentTarget.open)}><summary>Aktivitas sumber terkait · bukan failure/repair register</summary>{sourceOpen&&<><p>Rekam Mart berikut memakai izin aset existing. Filter tanggalnya adalah aktivitas actual_start/source_changed_at, terpisah dari periode KPI di atas. Tidak ada konversi WO menjadi failure atau repair.</p><AssetMaintenanceEvidence key={selected.asset} canonicalId={selected.asset}/></>}</details></SectionCard>
      <SectionCard><h3>Definisi, provenance dan audit</h3><p>Failure identity, jam operasi berkualitas, active repair, revisi/exclusion dan kebijakan window memerlukan source-owner serta engineer sign-off. Persetujuan inspeksi, status WO, nilai PI terbaru atau CI PASS tidak memenuhi gate tersebut.</p><p>KPI legacy tetap memiliki arti/formula lamanya; bukan hasil module qualified ini. Policy operasional, operational evaluation dan publikasi KPI tetap dinonaktifkan.</p><Link className="text-link" href="/data-quality">Buka Data Trust sesuai izin →</Link></SectionCard>
    </>}
  </div>;
}

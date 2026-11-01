'use client';
import PdmDate from './PdmDate';
import PdmSourceHistory from './PdmSourceHistory';
import PdmTrendEligibility from './PdmTrendEligibility';
import {formatRecordedInstant} from '../lib/pdm-date';
import {useEffect,useState} from 'react';
import {engineeringRequest,EngineeringHttpError} from '../lib/engineering-http';
import {originalValue,type QaPage} from '../lib/product-records';
import type {MeasurementEvent} from '../lib/pdm-input';
import {emptyHistoryContext,pointQuery,samplePlot,type HistoryContext} from '../lib/pdm-history';
import {Button,EmptyState,Feedback,HelpDetails,Pagination,SectionCard,StatusBadge,TableFrame} from './ui';

export default function PdmHistory({query,onExpired,onSelect,context=emptyHistoryContext,onContextChange}:{query:string;onExpired:()=>void;onSelect:(id:string)=>void;context?:HistoryContext;onContextChange?:(value:HistoryContext)=>void}){
 const [kind,setKind]=useState(context.kind),[sourceOpened,setSourceOpened]=useState(context.kind==='excel');
 const [offset,setOffset]=useState(context.nativeOffset),[nativeLimit,setNativeLimit]=useState<1|10|25>(context.nativeLimit),[point,setPoint]=useState(context.point),[quantity,setQuantity]=useState(context.quantity),[filters,setFilters]=useState(pointQuery(context.point,context.quantity));
 const [page,setPage]=useState<QaPage<MeasurementEvent>|null>(null),[error,setError]=useState(''),[retryable,setRetryable]=useState(false),[refresh,setRefresh]=useState(0),[selected,setSelected]=useState('');
 useEffect(()=>{setKind(context.kind);if(context.kind==='excel')setSourceOpened(true);},[context.kind]);
 useEffect(()=>{setPoint(context.point);setQuantity(context.quantity);setFilters(pointQuery(context.point,context.quantity));},[context.point,context.quantity]);
 useEffect(()=>{setOffset(context.nativeOffset);setNativeLimit(context.nativeLimit);},[context.nativeOffset,context.nativeLimit]);
 useEffect(()=>{setSelected('');},[query,filters,offset,nativeLimit]);
 useEffect(()=>{
  if(kind!=='native')return;
  let active=true;setPage(null);setError('');setRetryable(false);
  engineeringRequest(`inspections/measurement-history?offset=${offset}&limit=${nativeLimit}${query}${filters}`).then(raw=>{
   const response=raw as QaPage<MeasurementEvent>&{filter_scope?:string;event_time_basis?:string};
   if(response.filter_scope!=='AUTHORIZED_POPULATION'||response.event_time_basis!=='MEASURED_AT'||response.limit!==nativeLimit||response.offset!==offset||!Number.isSafeInteger(response.total)||response.total<0||!Array.isArray(response.items)||response.items.length!==Math.min(nativeLimit,Math.max(0,response.total-offset))||response.has_more!==(offset+nativeLimit<response.total))throw Error('PDM_CONTRACT_UNAVAILABLE');
   if(active)setPage(response);
  }).catch(e=>{
   if(!active)return;
   const denied=e instanceof EngineeringHttpError&&e.status===403,expired=e instanceof EngineeringHttpError&&e.status===401;
   const oversized=e instanceof EngineeringHttpError&&e.status===502&&e.code==='QA_BODY_LIMIT_EXCEEDED';
   setError(denied?'Akun ini tidak memiliki akses ke pengukuran asli.':expired?'Sesi berakhir. Silakan masuk kembali.':oversized?'Respons histori terlalu besar. Pilih 10 atau 1 event per halaman; nilai tidak dipotong.':'Riwayat measurement tidak tersedia; tidak mengganti nilai dengan nol.');setRetryable(!denied&&!expired&&!oversized);
   if(expired)onExpired();
  });
  return()=>{active=false;};
 },[offset,query,filters,onExpired,kind,refresh,nativeLimit]);
 const events=page?.items??[],ids=[...new Set(events.map(x=>x.record_id))],selectedEvents=events.filter(e=>e.record_id===selected),plot=samplePlot(selectedEvents);
 function choose(next:'native'|'excel'){setKind(next);if(next==='excel')setSourceOpened(true);onContextChange?.({...context,kind:next});}
 return <>
  <nav className="pdm-history-kinds" aria-label="Jenis riwayat PdM"><Button aria-pressed={kind==='native'} variant={kind==='native'?'primary':'outline'} onClick={()=>choose('native')}>Pengukuran Asli</Button><Button aria-pressed={kind==='excel'} variant={kind==='excel'?'primary':'outline'} onClick={()=>choose('excel')}>Sumber Excel</Button></nav>
  <p className="section-note">Pengukuran asli, inspeksi dan kelompok Excel adalah populasi terpisah. Filter workbook/sheet mengikuti akses sumber; label workbook tidak dipetakan otomatis ke aset atau titik.</p>
  {context.originRecord&&<div className="page-actions"><Button onClick={()=>onSelect(context.originRecord)}>Kembali ke inspeksi asal</Button></div>}
  {sourceOpened&&<div hidden={kind!=='excel'}><PdmSourceHistory onExpired={onExpired} onSelect={onSelect}/></div>}
  <div hidden={kind!=='native'}><SectionCard className="pdm-history"><p className="eyebrow">Event asli · waktu pengukuran</p><h2>Pengukuran Asli</h2><p className="section-note">Nilai, unit dan waktu asli dari inspeksi. Rekam provisional serta estimasi sumber tidak dimasukkan ke grafik ini.</p>
   <HelpDetails title="Cakupan & urutan event"><p>Filter aset/metode/status/pencarian dan interval di atas berlaku pada seluruh populasi native berotorisasi. Basis interval adalah measured_at, bukan waktu inspeksi/input. Urutan stabil: ID inspeksi lalu indeks measurement, bukan urutan waktu atau frekuensi harian. Nilai revisi terdahulu tetap tersedia pada audit inspeksi.</p></HelpDetails>
   <form className="filter-grid" onSubmit={e=>{e.preventDefault();setOffset(0);setFilters(pointQuery(point,quantity));onContextChange?.({...context,kind:'native',point,quantity,nativeOffset:0});}}><label>Titik exact<input value={point} maxLength={200} onChange={e=>setPoint(e.target.value)}/></label><label>Parameter exact<input value={quantity} maxLength={120} onChange={e=>setQuantity(e.target.value)}/></label><Button type="submit">Terapkan filter measurement</Button></form>
   <label className="pdm-page-size">Event per halaman<select aria-label="Event per halaman" value={nativeLimit} onChange={e=>{const n=Number(e.target.value);if(n!==1&&n!==10&&n!==25)return;setNativeLimit(n);setOffset(0);onContextChange?.({...context,nativeLimit:n,nativeOffset:0});}}>{[1,10,25].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
   {error&&<Feedback error>{error}{retryable&&<Button onClick={()=>setRefresh(n=>n+1)}>Coba baca riwayat lagi</Button>}</Feedback>}{!page&&!error&&kind==='native'&&<p role="status">Memuat event measurement…</p>}
   {page&&<>
    <p className="section-note">{page.total} event pengukuran sesuai filter · {events.length} event di halaman ini. Bukan jumlah inspeksi atau kelompok Excel.</p>
    {events.length?<TableFrame label="Riwayat measurement asli" minWidth={1100}><table><thead><tr><th>Waktu / inspeksi</th><th>Aset / metode</th><th>Titik / parameter</th><th>Nilai asli / tipe</th><th>Unit</th><th>Status / provenance</th></tr></thead><tbody>{events.map(e=><tr key={`${e.record_id}:${e.revision}:${e.measurement_index}`}>
     <td><PdmDate value={e.measurement.measured_at} raw/><small className="table-subtext"><Button onClick={()=>onSelect(e.record_id)}>{e.record_id}</Button> · r{e.revision}</small></td>
     <td>{e.canonical_asset_id}<small className="table-subtext">{e.method} / {e.method_version}</small><details><summary>Konteks pengukuran</summary><p>Operasi: {e.operating_context??'UNKNOWN'}</p><p>Instrumen: {originalValue(e.method_extension?.instrument_ref)}</p><p>Prosedur: {originalValue(e.method_extension?.procedure_ref)}</p><p>Orientasi: {originalValue(e.method_extension?.orientation)}</p><p>Rujukan tersimpan; bukan bukti comparability yang disahkan.</p></details></td>
     <td>{e.measurement.point_ref??'UNKNOWN'}<small className="table-subtext">{e.measurement.quantity}</small></td><td>{originalValue(e.measurement.value)}<small className="table-subtext">{e.measurement.value===null?'null':typeof e.measurement.value}</small></td><td>{e.measurement.unit??'UNKNOWN'}</td><td><StatusBadge mode="raw-neutral" value={e.status}/><small className="table-subtext">{e.measurement.quality} · {e.measurement.provenance} · {e.inspector_ref}</small></td>
    </tr>)}</tbody></table></TableFrame>:<EmptyState title="Tidak ada measurement dalam filter server ini." detail="Tidak adanya measurement bukan bukti kondisi normal."/>}
    <Pagination meta={{...page,has_more:page.has_more&&page.offset+page.limit<=10000}} onChange={n=>{setOffset(n);setSelected('');onContextChange?.({...context,nativeOffset:n});}}/>
    <p className="section-note">Halaman {Math.floor(page.offset/page.limit)+1} dari {Math.max(1,Math.ceil(page.total/page.limit))} · maksimal {nativeLimit} event per halaman.{page.has_more&&page.offset+page.limit>10000?' Batas offset tercapai; persempit filter untuk melanjutkan.':''}</p>
    <PdmTrendEligibility events={selectedEvents}/>
    <h3>Sampel asli dalam satu inspeksi</h3><label>Plot sampel pada halaman ini (satu inspeksi)<select aria-label="Plot sampel pada halaman ini (satu inspeksi)" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Pilih inspeksi</option>{ids.map(id=><option key={id}>{id}</option>)}</select></label>
    <p className="section-note">Hanya event halaman ini sesuai filter, dari satu inspeksi/revisi. Jika inspeksi memiliki event di halaman lain, plot ini belum lengkap. Tidak ada penggabungan lintas inspeksi atau interpolasi.</p>
    {plot.points.length?<RawScatter points={plot.points} unit={plot.unit}/>:<EmptyState title="Sampel satu inspeksi belum dapat diplot" detail={plot.reason}/>}
   </>}
  </SectionCard></div>
 </>;
}
export function RawScatter({points,unit}:{points:{time:number;value:number;label:string}[];unit:string}){
 const times=points.map(p=>p.time),values=points.map(p=>p.value),minT=Math.min(...times),maxT=Math.max(...times),minV=Math.min(...values),maxV=Math.max(...values);
 const x=(v:number)=>60+(maxT===minT?0.5:(v-minT)/(maxT-minT))*680,y=(v:number)=>220-(maxV===minV?0.5:(v-minV)/(maxV-minV))*160;
 return <figure className="pdm-raw-plot"><svg role="img" aria-label={`Sampel measurement asli, ${unit}; titik tanpa garis interpolasi`} viewBox="0 0 800 280"><title>Sampel asli, bukan diagnosis atau seri lintas inspeksi</title><path d="M60 50 V220 H740" fill="none" stroke="currentColor"/>{points.map((p,i)=><circle key={i} cx={x(p.time)} cy={y(p.value)} r="5" fill="var(--chart)"><title>{formatRecordedInstant(p.label)} · {p.value} {unit}</title></circle>)}<text x="60" y="30" fill="currentColor">{minV} – {maxV} {unit}</text><text x="60" y="247" fill="currentColor">{formatRecordedInstant(points.find(p=>p.time===minT)?.label)}</text><text x="60" y="270" fill="currentColor">hingga {formatRecordedInstant(points.find(p=>p.time===maxT)?.label)}</text></svg><figcaption>{points.length} event asli pada timestamp yang dilaporkan. Tabel di atas menjadi alternatif aksesibel.</figcaption></figure>;
}

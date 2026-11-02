"use client";
import {useEffect, useState, useRef} from 'react';
import {reliabilityApi, type MaintenanceEventView, type Page} from '../lib/api';
import {conflictingWorkOrders, evidenceError, evidenceErrorKind, maintenanceFilters, maintenanceFilterError, validateMaintenance} from '../lib/asset-evidence';
import {Button, EmptyState, ErrorState, LoadingState, Pagination, TableFrame} from './ui';

import {WorkOrderClock,WorkOrderSourceDetail} from './WorkOrderSourceDetail';
const fields = [['me_wo','Rujukan WO (persis)'],['me_status','Status sumber'],['me_type','Kategori kanonis (persis)'],['me_from','Dari waktu (ISO-8601 + zona)'],['me_to','Sampai waktu (ISO-8601 + zona)']] as const;
export default function AssetMaintenanceEvidence({canonicalId}: {canonicalId: string}) {
  const [query, setQuery] = useState(''), [ready, setReady] = useState(false), [retry, setRetry] = useState(0);
  const [page, setPage] = useState<Page<MaintenanceEventView> | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState<string | null>(null);
  const [errorKind,setErrorKind]=useState<'access'|'session'|'request'|'service'>('service');
  const returnFocus=useRef<string|null>(null);
  const filterParams = new URLSearchParams(query);for(const key of [...filterParams.keys()]) if(!key.startsWith('me_') || key==='me_record')filterParams.delete(key);
  const filterQuery=filterParams.toString();
  useEffect(() => {const read = () => {setQuery(location.search); setReady(true);}; read(); window.addEventListener('popstate', read); return () => window.removeEventListener('popstate', read);}, [canonicalId]);
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    const filters = maintenanceFilters(new URLSearchParams(filterQuery), canonicalId);
    setLoading(true); setPage(null); setError(null);
    const invalid = maintenanceFilterError(filters); if (invalid) {setError(invalid);setErrorKind('request');setLoading(false);return;}
    reliabilityApi.maintenance(filters).then(p => {validateMaintenance(p, canonicalId, filters.offset ?? 0); if (!cancelled) setPage(p);}).catch(e => {if (!cancelled) {setError(evidenceError(e));setErrorKind(evidenceErrorKind(e));}}).finally(() => {if (!cancelled) setLoading(false);});
    return () => {cancelled = true;};
  }, [canonicalId, filterQuery, ready, retry]);
  function navigate(q: URLSearchParams) {q.set('tab','maintenance'); history.pushState({},'',`${location.pathname}?${q}`); setQuery('?' + q);}
  function apply(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget), q = new URLSearchParams(query);
    for (const [key] of fields) {const value = String(data.get(key) ?? '').trim(); if (value) q.set(key,value); else q.delete(key);}
    q.set('me_sort',String(data.get('me_sort'))); q.delete('me_offset'); q.delete('me_record'); navigate(q);
  }
  const q = new URLSearchParams(query), selected = q.get('me_record'), row = page?.items.find(x => x.canonical_id === selected), conflicts = conflictingWorkOrders(page?.items ?? []);
  useEffect(()=>{if(loading || !page)return;if(selected)document.getElementById('maintenance-source-detail')?.focus();else if(returnFocus.current){document.getElementById('maintenance-open-'+encodeURIComponent(returnFocus.current))?.focus();returnFocus.current=null;}},[selected,page,loading]);
  return <section className="asset-evidence" aria-label="Evidence pemeliharaan Maximo">
    <h3>Evidence pemeliharaan · Maximo</h3>
    <p>Lingkup aset persis · BSR / IP. Register berisi rekam sumber kanonis, bukan jumlah kegagalan atau WO unik.</p>
    <form key={query} onSubmit={apply}><div className="filter-grid">{fields.map(([key,label]) => <label key={key}>{label}<input name={key} defaultValue={q.get(key) ?? ''} maxLength={200} type="text"/></label>)}<label>Urutan<select name="me_sort" defaultValue={q.get('me_sort') ?? 'date_desc'}><option value="date_desc">Tanggal terbaru</option><option value="date_asc">Tanggal terlama</option><option value="status">Status sumber</option></select></label></div><div className="page-actions"><Button variant="primary" type="submit">Terapkan filter evidence</Button><Button type="button" onClick={() => {const next = new URLSearchParams(query); for (const key of [...fields.map(([k])=>k),'me_sort','me_offset','me_record']) next.delete(key); navigate(next);}}>Bersihkan filter</Button></div></form>
    <p className="section-note">Filter tanggal dan urutan memakai actual_start bila ada; jika kosong memakai source_changed_at. Waktu sinkronisasi dan proyeksi: TIDAK DIEKSPOS. Kesegaran tidak disimpulkan dari tanggal WO.</p>
    {loading && <LoadingState/>}{!loading && error && <ErrorState message={error} variant={errorKind} onRetry={() => setRetry(n=>n+1)}/>}
    {!loading && !error && page && <><p role="status">{page.meta.total} rekam sumber pada filter ini · maksimum 25 per halaman.</p>{conflicts.size > 0 && <p role="note">UNRESOLVED · Ada rujukan WO sama pada identitas rekam berbeda di halaman ini. Semua rekam dipertahankan; tidak digabung atau dihitung sebagai kegagalan.</p>}
      {page.items.length === 0 ? <EmptyState title="Tidak ada rekam pemeliharaan pada filter ini." detail="Hasil kosong tidak membuktikan aset bebas gangguan atau join sumber lengkap."/> : <TableFrame minWidth={1000} label="Register evidence Maximo"><table><thead><tr><th>WO / rekam sumber</th><th>Jenis / status sumber</th><th>Mulai aktual</th><th>Selesai aktual</th><th>Terakhir Diubah di Maximo</th><th>Detail</th></tr></thead><tbody>{page.items.map(item => <tr key={item.canonical_id}><td><strong>{item.source_detail ? item.source_detail.work_order_number ?? 'BELUM TERSEDIA' : 'Nomor WO · TIDAK DIEKSPOS'}</strong>{item.work_order_id && conflicts.has(item.work_order_id) && <small className="table-subtext">Identitas WO konflik · halaman ini</small>}</td><td>{item.classification?.raw_work_type ?? (item.classification ? 'BELUM TERSEDIA' : 'TIDAK DIEKSPOS')}<small className="table-subtext">Kategori kanonis: {item.event_type ?? (item.classification?.state === 'UNMAPPED' ? 'BELUM DIPETAKAN' : 'BELUM TERSEDIA')} · {!item.classification ? 'TIDAK DIEKSPOS' : item.classification.state === 'UNMAPPED' ? 'BELUM DIPETAKAN' : item.classification.state === 'MISSING_RETAINED_TYPE' ? 'BELUM TERSEDIA' : item.classification.confidence === 'UNRESOLVED' ? 'BELUM DIVERIFIKASI' : 'Kode sumber sesuai'}</small><br/>{item.status?.trim() ? <span className="status-badge neutral">{item.status}</span> : 'BELUM TERSEDIA'}</td><td><WorkOrderClock value={item.actual_start}/></td><td><WorkOrderClock value={item.actual_finish}/></td><td><WorkOrderClock value={item.source_changed_at}/></td><td><button id={"maintenance-open-"+encodeURIComponent(item.canonical_id)} type="button" className="text-link-button" onClick={() => {const next = new URLSearchParams(query); next.set('me_record',item.canonical_id); navigate(next);}}>Buka rekam {item.source_detail?.work_order_number ?? item.id}</button></td></tr>)}</tbody></table></TableFrame>}
      <Pagination meta={page.meta} onChange={offset => {const next = new URLSearchParams(query); next.set('me_offset',String(offset)); next.delete('me_record'); navigate(next);}}/>
      {selected && <section id="maintenance-source-detail" tabIndex={-1} aria-label="Detail sumber Maximo"><h3>Detail rekam sumber Maximo</h3>{!row ? <p>Rekam terpilih tidak ada pada halaman dan filter saat ini. Tidak ada pencarian massal atau pemilihan WO lain otomatis.</p> : <WorkOrderSourceDetail row={row}/>}<Button onClick={() => {returnFocus.current=selected; const next = new URLSearchParams(query); next.delete('me_record'); navigate(next);}}>Kembali ke register evidence</Button></section>}
    </>}
  </section>;
}

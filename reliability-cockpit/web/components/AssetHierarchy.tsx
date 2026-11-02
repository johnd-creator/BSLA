'use client';

import {useEffect,useState} from 'react';
import {ApiError,reliabilityApi} from '../lib/api';
import type {HierarchyNode,HierarchyView} from '../lib/asset-hierarchy';
import {formatDate} from '../lib/format';
import {EmptyState,ErrorState,Identifier,LoadingState,Pagination,TableFrame} from './ui';

const ancestorLabels:Record<HierarchyView['ancestor_state'],string>={
  NO_RETAINED_PARENT:'Ujung parent yang tersimpan; akar sumber belum dipastikan.',
  UNRESOLVED_PARENT:'Parent tercatat, tetapi rekam parent belum tersimpan.',
  OUT_OF_SCOPE_PARENT:'Rujukan parent berada di luar scope identitas yang diizinkan.',
  CYCLE:'Siklus parent terdeteksi; penelusuran dihentikan.',
  DEPTH_LIMIT:'Batas penelusuran parent tercapai; jalur belum lengkap.',
};
const name=(node:HierarchyNode)=>node.source_asset_number??node.canonical_id;

export default function AssetHierarchy({canonicalId}:{canonicalId:string}){
  const [open,setOpen]=useState(false),[node,setNode]=useState(canonicalId),[offset,setOffset]=useState(0);
  const [data,setData]=useState<HierarchyView|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{
    if(!open)return;
    let active=true;setBusy(true);setData(null);setError('');
    reliabilityApi.hierarchy(canonicalId,node,offset).then(value=>{if(active)setData(value);}).catch(reason=>{
      if(active)setError(reason instanceof ApiError&&reason.status===403
        ?'Izin membaca konteks hierarki teknis belum tersedia untuk sesi ini.'
        :'Konteks hierarki belum tersedia. Data sumber belum dapat dipastikan.');
    }).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[canonicalId,node,offset,open,retry]);
  function select(ref:string){setNode(ref);setOffset(0);}
  return <details className="section-card advanced-evidence" onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>Hierarki aset Maximo · parent dan komponen tersimpan</summary>
    {open&&<div aria-live="polite">
      <p className="section-note">Cakupan parsial dari relasi parent Maximo yang sudah tersimpan. Anak yang belum tersimpan tidak berarti peralatan tanpa komponen. Peran sistem/peralatan/komponen belum diverifikasi; tipe sumber ditampilkan apa adanya.</p>
      {busy&&<LoadingState/>}
      {error&&<ErrorState message={error} onRetry={()=>setRetry(value=>value+1)}/>}
      {!busy&&!error&&data&&<>
        <p>{ancestorLabels[data.ancestor_state]} {data.unresolved_parent_ref&&<Identifier value={data.unresolved_parent_ref}/>}</p>
        {data.ancestors.length>0&&<div><p className="eyebrow">Parent tersimpan di atas aset terdaftar</p><ol>{data.ancestors.map(item=><li key={item.canonical_id}>{name(item)} · {item.description??'Deskripsi belum tersedia'} · {item.registered?'Terdaftar':'Konteks teknis'}</li>)}</ol></div>}
        <nav aria-label="Jalur hierarki dalam aset terdaftar"><ol>{data.path.map(item=><li key={item.canonical_id}><button type="button" className="text-link" aria-current={item.canonical_id===node?'location':undefined} onClick={()=>select(item.canonical_id)}>{name(item)}</button></li>)}</ol></nav>
        <h3>{name(data.node)}</h3><p>{data.node.description??'Deskripsi belum tersedia'}{data.node.description_shortened?' … (pratinjau deskripsi)':''}</p>
        <p className="section-note">{data.node.registered?'Aset terdaftar':'Konteks teknis; bukan keanggotaan Asset Register'} · Tipe sumber: {data.node.asset_type??'UNKNOWN'} · Status sumber: {data.node.status??'UNKNOWN'}. Flag anak sumber: {data.node.source_has_children===null?'UNKNOWN':data.node.source_has_children?'Ya':'Tidak'}. Jumlah anak tersimpan: {data.total}.</p>
        {data.items.length?<TableFrame minWidth={620} label="Anak langsung yang tersimpan"><table><thead><tr><th>Aset / komponen</th><th>Tipe / status sumber</th><th>Keanggotaan</th><th>Waktu ubah sumber</th></tr></thead><tbody>{data.items.map(item=><tr key={item.canonical_id}><td><button type="button" className="text-link" onClick={()=>select(item.canonical_id)} disabled={data.path.length>data.depth_limit}>Buka {name(item)}</button><small className="table-subtext">{item.description??'Deskripsi belum tersedia'}{item.description_shortened?' … (pratinjau)':''}</small></td><td>{item.asset_type??'UNKNOWN'}<small className="table-subtext">{item.status??'UNKNOWN'}</small></td><td>{item.registered?'Terdaftar':'Konteks teknis'}</td><td>{formatDate(item.source_updated_at)}</td></tr>)}</tbody></table></TableFrame>:<EmptyState title="Tidak ada anak langsung pada halaman data tersimpan ini." detail="Kelengkapan hierarki Maximo belum dipastikan; ini bukan bukti leaf sumber."/>}
        <Pagination meta={{total:data.total,offset:data.offset,limit:data.limit,has_more:data.has_more}} onChange={setOffset}/>
        <p className="section-note">Relasi dan waktu ubah berasal dari Maximo tersimpan; bukan bukti sinkronisasi terbaru atau kondisi peralatan. Pembacaan ini tidak menambah aset ke Registry.</p>
      </>}
    </div>}
  </details>;
}

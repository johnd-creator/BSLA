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
const ref=/^asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}$/;
function locationState(root:string){
  const q=new URL(window.location.href).searchParams;
  const same=q.get('hierarchy_root')===root,node=q.get('hierarchy_node'),offset=q.get('hierarchy_offset')??'0';
  return {open:same&&q.get('hierarchy')==='1',node:same&&node&&ref.test(node)?node:root,
    offset:same&&/^\d{1,5}$/.test(offset)&&Number(offset)<=10000?Number(offset):0};
}

export default function AssetHierarchy({canonicalId}:{canonicalId:string}){
  const [open,setOpen]=useState(false),[node,setNode]=useState(canonicalId),[offset,setOffset]=useState(0);
  const [childrenOpen,setChildrenOpen]=useState(true);
  const [data,setData]=useState<HierarchyView|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{
    const restore=()=>{const s=locationState(canonicalId);setOpen(s.open);setNode(s.node);setOffset(s.offset);setChildrenOpen(true);};
    restore();window.addEventListener('popstate',restore);return ()=>window.removeEventListener('popstate',restore);
  },[canonicalId]);
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
  function navigate(nextOpen:boolean,nextNode=node,nextOffset=offset){
    const url=new URL(window.location.href);
    url.searchParams.set('hierarchy_root',canonicalId);url.searchParams.set('hierarchy',nextOpen?'1':'0');
    url.searchParams.set('hierarchy_node',nextNode);url.searchParams.set('hierarchy_offset',String(nextOffset));
    // Preserve framework history metadata and all unrelated asset-page parameters.
    if(url.href!==window.location.href)window.history.pushState(window.history.state,'',url);
    setOpen(nextOpen);setNode(nextNode);setOffset(nextOffset);setChildrenOpen(true);
  }
  function select(value:string){navigate(true,value,0);}
  return <details className="section-card advanced-evidence" open={open} onToggle={event=>{
    if(event.target===event.currentTarget&&event.currentTarget.open!==open)navigate(event.currentTarget.open);
  }}>
    <summary>Hierarki aset Maximo · parent dan komponen tersimpan</summary>
    {open&&<div aria-live="polite">
      <p className="section-note"><strong>Cakupan PARTIAL.</strong> Cakupan parsial dari relasi parent Maximo yang sudah tersimpan. Anak yang belum tersimpan tidak berarti peralatan tanpa komponen. Peran sistem/peralatan/komponen belum diverifikasi; tipe sumber ditampilkan apa adanya.</p>
      {busy&&<LoadingState/>}
      {error&&<ErrorState message={error} onRetry={()=>setRetry(value=>value+1)}/>}
      {!busy&&!error&&data&&<>
        <p>{ancestorLabels[data.ancestor_state]} {data.unresolved_parent_ref&&<Identifier value={data.unresolved_parent_ref}/>}</p>
        {data.ancestors.length>0&&<nav aria-label="Parent tersimpan di atas aset terdaftar"><p className="eyebrow">Parent tersimpan di atas aset terdaftar</p><ol>{data.ancestors.map(item=><li key={item.canonical_id}><button type="button" className="text-link-button" aria-current={item.canonical_id===node?'location':undefined} onClick={()=>select(item.canonical_id)}>{name(item)}</button> · {item.description??'Deskripsi belum tersedia'} · {item.registered?'Terdaftar':'Konteks teknis'}</li>)}</ol></nav>}
        <nav aria-label="Jalur hierarki dalam aset terdaftar"><ol>{data.path.map(item=><li key={item.canonical_id}><button type="button" className="text-link-button" aria-current={item.canonical_id===node?'location':undefined} onClick={()=>select(item.canonical_id)}>{name(item)}</button></li>)}</ol></nav>
        <h2>{name(data.node)}</h2><p>{data.node.description??'Deskripsi belum tersedia'}{data.node.description_shortened?' … (pratinjau deskripsi)':''}</p>
        <p className="section-note">{data.node.registered?'Aset terdaftar':'Konteks teknis; bukan keanggotaan Asset Register'} · Unit: <strong>{data.node.unit??'UNKNOWN'}</strong> · Peran: <strong>UNVERIFIED</strong> (belum diverifikasi).</p>
        <p className="section-note">Tipe sumber: {data.node.asset_type??'UNKNOWN'} · Status sumber: {data.node.status??'UNKNOWN'}. Flag anak sumber: {data.node.source_has_children===null?'UNKNOWN':data.node.source_has_children?'Ya':'Tidak'}. Jumlah anak {data.node_relation==='ANCESTOR'?'pada cabang yang diizinkan':'tersimpan'}: {data.total}.</p>
        {data.node_relation==='ANCESTOR'&&<p className="section-note">Konteks ancestor hanya membuka cabang yang terbukti menuju aset terdaftar ini. Cabang saudara dan seluruh anak parent tidak dienumerasi.</p>}
        <details open={childrenOpen} onToggle={event=>{if(event.target===event.currentTarget)setChildrenOpen(event.currentTarget.open);}}>
          <summary>Anak langsung · perluas atau tutup tingkat ini</summary>
          {data.items.length?<TableFrame minWidth={760} label="Anak langsung yang tersimpan"><table><thead><tr><th>Aset / komponen</th><th>Tipe / status sumber</th><th>Unit / peran</th><th>Keanggotaan</th><th>Waktu ubah sumber</th></tr></thead><tbody>{data.items.map(item=><tr key={item.canonical_id}><td><button type="button" className="text-link-button" onClick={()=>select(item.canonical_id)} disabled={data.node_relation!=='ANCESTOR'&&data.path.length>data.depth_limit}>Buka {name(item)}</button><small className="table-subtext">{item.description??'Deskripsi belum tersedia'}{item.description_shortened?' … (pratinjau)':''}</small></td><td>{item.asset_type??'UNKNOWN'}<small className="table-subtext">{item.status??'UNKNOWN'}</small></td><td>{item.unit??'UNKNOWN'}<small className="table-subtext">UNVERIFIED</small></td><td>{item.registered?'Terdaftar':'Konteks teknis'}</td><td>{formatDate(item.source_updated_at)}</td></tr>)}</tbody></table></TableFrame>:<EmptyState title="Tidak ada anak langsung pada halaman data tersimpan ini." detail="Kelengkapan hierarki Maximo belum dipastikan; ini bukan bukti leaf sumber."/>}
          <Pagination meta={{total:data.total,offset:data.offset,limit:data.limit,has_more:data.has_more&&data.offset+data.limit<=10000}} onChange={value=>navigate(true,node,value)}/>
        </details>
        {data.has_more&&data.offset+data.limit>10000&&<p>Batas paging tercapai; seluruh cabang belum ditampilkan.</p>}
        <p className="section-note">Relasi dan waktu ubah berasal dari Maximo tersimpan; bukan bukti sinkronisasi terbaru atau kondisi peralatan. Pembacaan ini tidak menambah aset ke Registry.</p>
      </>}
    </div>}
  </details>;
}

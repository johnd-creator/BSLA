type Proof={coordinate:string;raw_value:unknown};
type Estimate={label:'ESTIMASI';value:number;unit:string;method:string;gap_days:number;confidence:'LOW';notice:string;evidence:Proof[]};
export type DerivedField={field_id:string;cell:string;kind:string;label:string;unit:string;method:string;evidence:Proof[];note?:string|null;estimate?:Estimate};
export type SourceInterpretation={version:string;notice:string;source_sha256:string;canonical_eligible:false;persisted:false;fields:DerivedField[];date:{value:string;method:string;note:string;evidence:Proof[]}|null;row_context:{label:string;method:string;note:string;evidence:Proof[]}|null};
const raw=(v:unknown)=>v===null||v===undefined?'Kosong':typeof v==='object'?JSON.stringify(v):String(v);
function References({items}:{items:Proof[]}){return <ul>{items.map(p=><li key={p.coordinate}>{p.coordinate}: {raw(p.raw_value)}</li>)}</ul>;}
export function SourceEstimateDisclosure({fields,interpretation}:{fields:{field_id:string;cell:string;value:{raw_value:unknown}}[];interpretation:SourceInterpretation|null|undefined}){
 const visible=fields.some(f=>f.value.raw_value===null&&interpretation?.fields.some(d=>d.field_id===f.field_id&&d.cell===f.cell&&!!d.estimate));
 return visible?<p className="section-note pdm-source-preview-note" role="note">Pratinjau, sebagian nilai diestimasi</p>:null;
}
export function SourceInterpretationContext({value}:{value:SourceInterpretation|null|undefined}){
 if(!value)return null;
 return <details aria-label="Catatan pembacaan sumber"><summary>Catatan pembacaan sumber{value.date&&<> · Tanggal sumber: {value.date.value}</>}{value.row_context&&<> · {value.row_context.label}</>}</summary><p>{value.notice} Nilai asli dan klasifikasi impor tetap dipertahankan; tidak digunakan untuk alert, persetujuan atau evidence Case.</p>
 {value.row_context&&<div><strong>{value.row_context.label}</strong><p>{value.row_context.note}</p><details><summary>Bukti klasifikasi header</summary><p>{value.row_context.method}</p><References items={value.row_context.evidence}/></details></div>}
 {value.date&&<div><p>Tanggal sumber terbaca: <strong>{value.date.value}</strong> · {value.date.note}</p><details><summary>Bukti tanggal turunan</summary><p>{value.date.method}</p><References items={value.date.evidence}/></details></div>}
 <small>Versi interpretasi: {value.version} · terikat hash workbook pada jejak sumber.</small></details>;
}
export function SourceDerivedValue({value,original}:{value:DerivedField|undefined;original:unknown}){
 if(!value)return <span>{raw(original)}</span>;
 const estimate=original===null?value.estimate:undefined;
 const reading=estimate?`${estimate.value.toLocaleString('id-ID',{maximumFractionDigits:2,minimumFractionDigits:2})} ${estimate.unit}`:'';
 return <details className="pdm-source-reading"><summary aria-label={estimate?`Estimasi ${reading}, buka asal dan metode`:undefined}>{estimate?reading:<>{raw(original)} <small>{value.unit}</small></>}</summary>
 <p>Nilai asli: <strong>{raw(original)}</strong></p><p>{value.label} · unit dari header: {value.unit}</p>{value.note&&<p>{value.note}</p>}
 {estimate&&<div><p>{estimate.notice}</p><p>Keyakinan: rendah · jeda {estimate.gap_days} hari.</p><p>Metode estimasi: {estimate.method}</p><References items={estimate.evidence}/></div>}
 <p>Metode pembacaan header: {value.method}</p><References items={value.evidence}/>
 </details>;
}

import {rawPlot,type MeasurementEvent} from './pdm-input';
import {validRecordId,type Inspection} from './product-records';

export type HistoryContext={kind:'native'|'excel';point:string;quantity:string;originRecord:string;nativeOffset:number;nativeLimit:1|10|25};
export const emptyHistoryContext:HistoryContext={kind:'native',point:'',quantity:'',originRecord:'',nativeOffset:0,nativeLimit:25};
export const registerFilterKeys=['search','asset_id','method','status','since','until'] as const;
export function readHistoryContext(params:URLSearchParams):HistoryContext {
 const origin=params.get('from_inspection');
 const offset=Number(params.get('event_offset')??0),limit=Number(params.get('event_limit'));
 return {kind:params.get('history_kind')==='excel'?'excel':'native',point:params.get('point')??'',quantity:params.get('quantity')??'',originRecord:validRecordId(origin)?origin!:'',nativeOffset:Number.isSafeInteger(offset)&&offset>=0&&offset<=10000?offset:0,nativeLimit:limit===1||limit===10||limit===25?limit:25};
}
export function nativeFilterQuery(params:URLSearchParams):string {
 const filters=new URLSearchParams();
 for(const key of registerFilterKeys){const value=params.get(key);if(value)filters.set(key,value);}
 return filters.size?'&'+filters.toString():'';
}
export function historyHref(row:Inspection):string {
 const p=new URLSearchParams({pdm_view:'history',history_kind:row.input_capture?'excel':'native',from_inspection:row.record_id});
 // A provisional source label is never used as a canonical asset/point mapping.
 if(!row.input_capture){p.set('asset_id',row.canonical_asset_id);p.set('method',row.method);}
 return '/pdm?'+p.toString();
}
export function pointQuery(point:string,quantity:string):string {
 const p=new URLSearchParams();if(point)p.set('point',point);if(quantity)p.set('quantity',quantity);
 return p.size?'&'+p.toString():'';
}
export function preciseInstant(value:string|null|undefined):boolean {
 // Date-only, time-only and naive clocks must not be promoted to midnight/UTC.
 if(typeof value!=='string')return false;
 const p=/^(\d{4})-(\d{2})-(\d{2})[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.exec(value);
 const clock=/[Tt](\d{2}):(\d{2}):(\d{2})/.exec(value);
 return !!clock&&Number(clock[1])<24&&Number(clock[2])<60&&Number(clock[3])<60&&!!p&&Number(p[1])>0&&Number(p[2])>=1&&Number(p[2])<=12&&Number(p[3])>=1&&Number(p[3])<=new Date(Date.UTC(Number(p[1]),Number(p[2]),0)).getUTCDate()&&Number.isFinite(Date.parse(value));
}
export function samplePlot(events:MeasurementEvent[]):ReturnType<typeof rawPlot> {
 if(events.some(e=>e.canonical_asset_id!==events[0]?.canonical_asset_id))return {points:[],unit:'',reason:'Identitas aset berbeda. Nilai tetap terpisah pada tabel.'};
 if(events.some(e=>!preciseInstant(e.measurement.measured_at)))return {points:[],unit:'',reason:'Waktu ukur lengkap dengan zona waktu belum tersedia. Tanggal saja, jam saja, dan waktu belum diketahui tetap dibaca pada tabel; tidak diubah menjadi timestamp grafik.'};
 return rawPlot(events);
}
export type RecordedCriterion={label:string;state:'RECORDED'|'UNKNOWN'|'DIFFERENT'|'PENDING_ENGINEER_VALIDATION'};
export function historyEligibility(events:MeasurementEvent[]):RecordedCriterion[] {
 const field=(label:string,read:(e:MeasurementEvent)=>unknown):RecordedCriterion=>{
  const values=events.map(read);return {label,state:!values.length||values.some(v=>v===null||v===undefined||v==='')?'UNKNOWN':values.every(v=>v===values[0])?'RECORDED':'DIFFERENT'};
 };
 return [field('Rujukan aset',e=>e.canonical_asset_id),field('Titik dan parameter',e=>e.measurement.point_ref?JSON.stringify([e.measurement.point_ref,e.measurement.quantity]):null),field('Unit asli',e=>e.measurement.unit),field('Metode dan versi',e=>e.method_version?JSON.stringify([e.method,e.method_version]):null),
 {label:'Waktu ukur lengkap dengan zona waktu',state:events.length&&events.every(e=>preciseInstant(e.measurement.measured_at))?'RECORDED':'UNKNOWN'},
 field('Rujukan instrumen, prosedur dan orientasi',e=>e.method_extension?.instrument_ref&&e.method_extension.procedure_ref&&e.method_extension.orientation?JSON.stringify([e.method_extension.instrument_ref,e.method_extension.procedure_ref,e.method_extension.orientation]):null),field('Konteks operasi',e=>e.operating_context),
 {label:'Bukti kesetaraan acquisition, bandwidth dan mounting',state:'UNKNOWN'},
 {label:'Persetujuan engineering untuk tren lintas inspeksi',state:'PENDING_ENGINEER_VALIDATION'}];
}

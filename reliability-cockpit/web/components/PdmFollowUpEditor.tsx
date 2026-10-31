import type {Entry} from '../lib/pdm-input';
import {Button} from './ui';
export default function PdmFollowUpEditor({entry,onChange,busy,section='all'}:{entry:Entry;onChange:(change:Partial<Entry>)=>void;busy:boolean;section?:'all'|'analysis'|'references'}){
 const refs=entry.srReferences??[];
 function setSr(key:string,change:{number?:string;note?:string}){onChange({srReferences:refs.map(row=>row.key===key?{...row,...change}:row)});}
 return <fieldset disabled={busy} id={section==='all'?'measurement-follow-up':undefined}><legend>{section==='references'?'Referensi SR Maximo':section==='analysis'?'Analisis manual':'Analisis manual & referensi SR'}</legend>{section!=='references'&&<>
 <p>Rangkuman penalaran manusia, terpisah dari nilai asli dan hipotesis; bukan diagnosis atau rekomendasi otomatis.</p>
 <label>Catatan analisis engineer (manual)<textarea aria-label="Catatan analisis engineer (manual)" rows={4} maxLength={6000} required={!!entry.analysisFollowUp} value={entry.analysisNotes??''} onChange={e=>onChange({analysisNotes:e.target.value})}/></label>
 <label>Saran tindak lanjut engineer (manual, opsional)<textarea aria-label="Saran tindak lanjut engineer (manual, opsional)" rows={3} maxLength={6000} value={entry.analysisFollowUp??''} onChange={e=>onChange({analysisFollowUp:e.target.value})}/></label>
 <p className="section-note">Saran berupa catatan manusia, belum menjadi rekam Recommendation atau persetujuan teknis. Persetujuan inspeksi tetap hanya review rekam NADI.</p>
 </>}{section!=='analysis'&&<><div className="section-heading"><h3>Referensi SR Maximo</h3><Button disabled={refs.length>=10} onClick={()=>onChange({srReferences:[...refs,{key:'sr-'+crypto.randomUUID(),number:'',note:''}]})}>Tambah referensi SR</Button></div>
 <p>SR berbeda dari Work Order. Nomor yang dilaporkan belum diverifikasi keberadaan, status atau kaitan asetnya. NADI tidak membuat SR atau menulis ke Maximo.</p>
 {!refs.length&&<p>Belum ada referensi SR yang dicatat.</p>}
 {refs.map((sr,i)=><fieldset key={sr.key}><legend>SR {i+1} · Belum terverifikasi</legend><label>Nomor SR {i+1}<input aria-label={"Nomor SR "+(i+1)} required maxLength={100} value={sr.number} onChange={e=>setSr(sr.key,{number:e.target.value})}/></label><label>Catatan tindak lanjut SR {i+1} (opsional)<textarea aria-label={"Catatan tindak lanjut SR "+(i+1)+" (opsional)"} maxLength={2000} value={sr.note} onChange={e=>setSr(sr.key,{note:e.target.value})}/></label><Button variant="destructive" aria-label={'Hapus referensi SR '+(i+1)} onClick={()=>onChange({srReferences:refs.filter(row=>row.key!==sr.key)})}>Hapus referensi</Button></fieldset>)}
 </>}</fieldset>;
}

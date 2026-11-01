import {preciseInstant} from './pdm-history';
export const performanceDefinition = 's4-candidate-1';
export const prerequisites = [
  {input:'Identitas peralatan',status:'AVAILABLE_VERIFIED',owner:'Source owner / Registry',reason:'Hanya identitas aset yang berhasil dibaca melalui izin existing; bukan persetujuan semantik KPI.'},
  {input:'Periode dan cakupan observasi',status:'AVAILABLE_UNAPPROVED',owner:'Reliability + Operations',reason:'Periode pilihan pengguna belum membuktikan cakupan lengkap atau aturan boundary/censor.'},
  {input:'Functional failure event',status:'MISSING',owner:'Reliability + Maintenance',reason:'WO, CM, PM dan failure code sumber tidak otomatis menjadi functional failure event.'},
  {input:'Operating exposure (jam)',status:'MISSING',owner:'Operations + Historian owner',reason:'Belum ada kontrak jam operasi berkualitas dan bukti kelengkapan; calendar hours dan nilai PI terbaru tidak menggantikannya.'},
  {input:'Active repair dan restoration',status:'MISSING',owner:'Maintenance + Reliability',reason:'Dataset qualified repair belum tersedia. Kontrak aktivitas memiliki field waktu yang dapat kosong pada aset ini; keberadaan schema tidak membuktikan ketersediaan nilainya. Waiting/planned downtime tetap berbeda.'},
  {input:'Duplicate, reopen, overlap dan censor',status:'MISSING',owner:'Reliability + Contract reviewer',reason:'Aturan identitas episode, revisi, supersession dan exclusion belum disahkan.'},
  {input:'Dataset failure/repair berizin',status:'BLOCKED',owner:'Data owner + Contract reviewer',reason:'Endpoint qualified failure/exposure/repair belum tersedia. Tidak ada pencarian atau join otomatis untuk mengisinya.'},
] as const;
export function performanceInput(asset:string,start:string,end:string):string|null {
  if(!asset.trim() || asset.trim().length>200)return 'Pilih referensi aset kanonis yang persis (maksimum 200 karakter).';
  if(start.endsWith('-00:00')||end.endsWith('-00:00')||!preciseInstant(start)||!preciseInstant(end)||Date.parse(start)>=Date.parse(end))return 'Gunakan waktu ISO-8601 lengkap dengan zona dan akhir setelah awal. Periode ini tetap belum disahkan sebagai window KPI.';
  return null;
}
export function performanceHref(asset:string,start:string,end:string) {return '/reports?'+new URLSearchParams({report_view:'reliability',rp_asset:asset,rp_start:start,rp_end:end});}

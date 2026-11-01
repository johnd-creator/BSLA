// Test/visual entry ONLY. No application route, API, stored QA or source imports.
import {SectionCard,TableFrame} from '../components/ui';
const points=[['2026-10-01T00:00:00Z',1],['2026-10-04T03:10:00Z',0],['2026-10-11T05:00:00Z',2],['2026-10-13T01:30:00Z',3],['2026-10-29T08:00:00Z',1.5],['2026-11-10T00:10:00Z',4],['2026-11-20T02:00:00Z',2.7]] as const;
export default function PdmTrendDemonstrator(){
 const start=Date.parse(points[0][0]),end=Date.parse(points.at(-1)![0]);
 return <div className="product-workspace"><h1>Demonstrator histori · SINTETIS</h1><p>Hanya fixture visual Sprint 2. Nilai, waktu, aset, titik dan rujukan di sini dibuat untuk pengujian; bukan data tersimpan, hasil pengukuran atau persetujuan engineer. Tidak tersedia sebagai route aplikasi NADI.</p>
  <SectionCard><h2>Contoh calon tampilan setelah kebijakan disahkan</h2><p>asset:SYNTHETIC-DEMO · point:DEMO · unit-SYNTHETIC. Ini bukan bukti comparability. Implementasi produksi tetap menolak tren lintas inspeksi sampai keputusan engineering diberikan.</p>
   <figure className="pdm-raw-plot"><svg role="img" aria-label="Grafik demonstrator sintetis: tujuh titik, waktu contoh tidak beraturan, tanpa interpolasi" viewBox="0 0 800 280"><title>SYNTHETIC ONLY — bukan pengukuran atau seri yang disahkan</title><path d="M60 30 V220 H740" fill="none" stroke="currentColor"/>{points.map(([time,value])=><circle key={time} cx={60+(Date.parse(time)-start)/(end-start)*680} cy={220-value/4*160} r="5" fill="var(--chart)"><title>{time} · {value} unit-SYNTHETIC</title></circle>)}<text x="60" y="25" fill="currentColor">unit-SYNTHETIC · tanpa grade kondisi</text><text x="60" y="250" fill="currentColor">1 Oktober–20 November 2026 · waktu contoh UTC</text></svg><figcaption>Tujuh sampel contoh. Jeda tetap kosong; tidak ada pengisian interval, garis interpolasi atau estimasi.</figcaption></figure>
   <TableFrame minWidth={600} label="Tabel alternatif demonstrator sintetis"><table><thead><tr><th>Rujukan contoh</th><th>Timestamp contoh UTC</th><th>Nilai sintetis</th><th>Unit contoh</th></tr></thead><tbody>{points.map(([time,value],i)=><tr key={time}><td>inspection:SYNTHETIC-DEMO-{i+1}</td><td>{time}</td><td>{value}</td><td>unit-SYNTHETIC</td></tr>)}</tbody></table></TableFrame>
  </SectionCard>
 </div>;
}

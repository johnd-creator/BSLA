import type {AssetConditionEvidence} from '../lib/api';
import {Identifier} from './ui';
export default function AssetCrosswalkInventory({data}: {data: AssetConditionEvidence}) {
  const verified = data.mapping_readiness === 'MAPPING_VERIFIED';
  return <details className="crosswalk-inventory"><summary>Crosswalk Maximo ↔ PI · {verified ? 'VERIFIED (status server)' : 'UNRESOLVED'}</summary>
    <p>Aset kanonis: <Identifier value={data.canonical_asset_id}/></p><p>Pemilik identitas: Registry / governance Mart Maximo. Pemilik signal: PI Collector dan persetujuan signal tersimpan. Maximo equipment reference ada pada identitas aset; tidak ada join berbasis nama.</p>
    {!verified && <p>{data.mapping_readiness === 'MAPPING_AMBIGUOUS' ? 'Mapping ganda atau konflik; evidence tidak boleh dipakai.' : 'Identitas belum dapat dipastikan dari kontrak ini. Ini tidak membuktikan tabel mapping kosong.'}</p>}
    {data.items.map(({evidence:e}) => <dl className="asset-facts" key={e.signal_id}><div><dt>Mapping / signal</dt><dd>{e.mapping_id} / {e.signal_id}</dd></div><div><dt>AF element / attribute</dt><dd>{e.sources?.pi.af_element_ref ?? 'NOT_EXPOSED'} / {e.sources?.pi.attribute_ref ?? 'NOT_EXPOSED'}</dd></div><div><dt>Evidence pemilihan signal (bukan verifikasi mapping)</dt><dd>{e.provenance?.selection_evidence_ref ?? 'NOT_EXPOSED'}</dd></div></dl>)}
    {verified && data.items.length === 0 && <p>Identitas VERIFIED, tetapi belum ada evidence signal. Referensi AF/mapping tidak diekspos pada respons kosong; tidak ditebak.</p>}
    <p>Metode, pemilik keputusan dan tanggal verifikasi mapping: NOT_EXPOSED. Inventori kandidat lengkap: BLOCKED_BY_CURRENT_CONTRACT. Rute pi-mapping tidak tersedia pada gateway ini; hak baca tidak diperluas. Kandidat, duplicate, missing dan FORBIDDEN memerlukan register keputusan source owner; UI ini tidak menyimpan atau menyetujui mapping.</p>
    <p>Local DCS Historian: DISCOVERY_ONLY. Kondisi peralatan dan kesiapan MTBF/MTTR: NOT_ELIGIBLE.</p>
  </details>;
}

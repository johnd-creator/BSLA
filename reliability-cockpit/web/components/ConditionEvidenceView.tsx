import {idText, statusLabel} from '../lib/id-copy';
import type {AssetConditionEvidence} from '../lib/api';
import AssetCrosswalkInventory from './AssetCrosswalkInventory';
const stamp = (value: string | null | undefined) => value ?? 'UNKNOWN';
const flag = (value: boolean | null) => value == null ? 'UNKNOWN' : String(value);
function originalValue(value: AssetConditionEvidence['items'][number]['evidence']['value']) {
  if (value === null) return 'NULL · nilai tidak tersedia';
  if (typeof value === 'object') return `name=${value.name ?? 'UNKNOWN'}; code=${value.code ?? 'UNKNOWN'}; is_system=${value.is_system ?? 'UNKNOWN'}`;
  return String(value);
}
export default function ConditionEvidenceView({data, observedAt = null}: {data: AssetConditionEvidence; observedAt?: string | null}) {
  return <>
    <p className="section-note">PI · {statusLabel(data.mapping_readiness)} · {data.statuses.map(statusLabel).join(' · ')}</p>
    <p>Nilai terbaru yang telah diproyeksikan · histori NOT_QUALIFIED. Kontrak histori kanonis belum tersedia; tidak ada pengambilan historian, interpolasi, atau trending.</p>
    {data.items.length === 0 ? <p>{idText('No governed condition evidence available. Verified equipment identity and approved signals are required. Equipment condition remains unknown.')}</p> : <div className="asset-record-list">{data.items.map(({evidence: e, freshness, projected_at, statuses}) => <article className="asset-record" key={e.signal_id}><div>
      <h3>{e.semantic_name}</h3><p className="evidence-value">{originalValue(e.value)} {e.unit ?? '· unit UNKNOWN'}</p>
      <small>{e.value_type} · {statuses.map(statusLabel).join(' · ')}</small>
      <dl className="asset-facts"><div><dt>Waktu pengukuran sumber</dt><dd>{stamp(e.source_timestamp)}</dd></div><div><dt>Dikoleksi</dt><dd>{stamp(e.collected_at)}</dd></div><div><dt>Diproyeksikan ke Mart</dt><dd>{stamp(projected_at)}</dd></div><div><dt>Diamati UI (jam browser)</dt><dd>{stamp(observedAt)}</dd></div></dl>
      <p>Kesegaran koleksi: {statusLabel(freshness.collector)} · sumber: {statusLabel(freshness.source)} · proyeksi: {statusLabel(freshness.projection)} · mapping: {statusLabel(freshness.mapping)}</p>
      <p>Kualitas asli · Good: {flag(e.quality_good)} · Questionable: {flag(e.quality_questionable)} · Substituted: {flag(e.quality_substituted)} · Annotated: {flag(e.quality_annotated)}</p>
      <details><summary>Detail sumber PI · {e.signal_id}</summary><dl className="asset-facts">{Object.entries({"Aset kanonis":e.canonical_asset_id ?? data.canonical_asset_id,"Signal ID":e.signal_id,"Mapping ID":e.mapping_id,"Versi kontrak":e.contract_version,"Sumber PI":e.sources?.pi.pi_source_id,"AF server":e.sources?.pi.af_server_ref,"AF database":e.sources?.pi.af_database_ref,"AF element":e.sources?.pi.af_element_ref,"Attribute":e.sources?.pi.attribute_ref,"Nama attribute":e.sources?.pi.attribute_name,"Status mapping sumber":e.sources?.pi.mapping_status,"Peran mapping":e.sources?.pi.mapping_role,"Evidence persetujuan signal":e.provenance?.selection_evidence_ref,"Pemberi persetujuan signal":e.provenance?.selection_approved_by,"Tanggal persetujuan signal":e.provenance?.selection_approved_at,"Batas sumber":e.provenance?.source_boundary}).map(([name,value]) => <div key={name}><dt>{name}</dt><dd>{value ?? 'NOT_EXPOSED'}</dd></div>)}</dl><p>Persetujuan signal bukan tanggal atau metode verifikasi mapping. Status kualitas sumber tidak menentukan kesehatan peralatan.</p></details>
    </div></article>)}</div>}
    <p className="section-note">Siklus kolektor terakhir berhasil: {stamp(data.collector_last_success_at)} · upaya proyeksi terakhir: {stamp(data.latest_attempt_at)}. Jam UI tidak membuktikan data baru atau segar.</p>
    <AssetCrosswalkInventory data={data}/>
  </>;
}

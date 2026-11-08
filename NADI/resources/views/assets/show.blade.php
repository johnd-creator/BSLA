<x-shell title="Detail Asset">
    <a class="back-link" href="{{ route('assets.index') }}">← Kembali ke daftar Asset</a>
    @if($record === null)
        <div class="panel connection-state">
            <span class="connection-icon" aria-hidden="true">↔</span>
            <h2>Belum terhubung</h2>
            <p>Detail aset belum dapat dibaca dari Reliability Mart.</p>
            <a class="button secondary" href="{{ request()->url() }}">Muat ulang</a>
        </div>
    @else
        <a class="button secondary" href="{{ route('reliability.index', ['asset_ref'=>$record['canonical_id']]) }}">Reliability · bukti & review tahunan</a>
        <div class="panel detail-panel">
            <div class="asset-detail-layout">
                <div class="asset-detail-facts">
                    <div class="detail-heading asset-detail-heading">
                        <div class="asset-heading-identity">
                            <p class="eyebrow">ASSET · {{ $record['site_code'] }} / {{ $record['organization_code'] }}</p>
                            <h2>{{ $record['source_asset_number'] ?? $record['canonical_id'] }}</h2>
                            <p>{{ $record['description'] ?? 'Deskripsi belum tersedia.' }}</p>
                            <span class="source-pill">Read only</span><a class="asset-mobile-action-link text-link" href="#asset-actions">Menu & tindakan untuk aset ↓</a>
                        </div>
                    </div>
                    <section class="asset-reliability-status" aria-labelledby="asset-reliability-title">
                        <div class="asset-reliability-heading">
                            <h3 id="asset-reliability-title">Reliability score</h3>
                            <span class="asset-reliability-pending">Belum cukup data</span>
                        </div>
                        <p>Reliability score belum tersedia. Data kosong bukan berarti aset sehat atau risikonya rendah.</p>
                        <details class="method-note"><summary>Data yang diperlukan untuk score</summary>
                        <ul class="asset-reliability-inputs">
                            <li>Kejadian gangguan yang sudah diverifikasi</li>
                            <li>Jam operasi dan availability dari historian</li>
                            <li>Riwayat pemeliharaan yang tervalidasi</li>
                            <li>Hasil PdM yang tervalidasi</li>
                        </ul>
                        <p class="asset-reliability-completeness">Kelengkapan data untuk score: <strong>Belum diverifikasi</strong>.</p></details>
                        @if($disruptionSummary['total'])<p class="asset-reliability-completeness">Log engineer: <strong>{{ $disruptionSummary['total'] }} kejadian tercatat</strong>, belum diverifikasi. <a class="text-link" href="#log-gangguan">Lihat catatan & kelengkapannya ↓</a></p>@endif
                    </section>
                    <dl class="detail-grid">
                        @foreach(['status'=>'Status sumber','asset_type'=>'Tipe aset','plant'=>'Plant','unit'=>'Unit','location_ref'=>'Lokasi','parent_asset_ref'=>'Parent asset'] as $field=>$label)
                            <div><dt>{{ $label }}</dt><dd>{{ $record[$field] ?? 'Belum tersedia' }}</dd></div>
                        @endforeach
                    </dl>
                    @if(isset($record['hierarchy_category']))
                        <dl class="detail-grid">
                            <div><dt>Kategori Excel engineer</dt><dd>{{ ['system' => 'System', 'equipment' => 'Equipment', 'component' => 'Component', 'part' => 'Part', 'unknown' => 'Belum dikategorikan'][$record['hierarchy_category']] }}</dd></div>
                            <div><dt>Dasar cakupan</dt><dd>{{ ['DIRECT_SOURCE_UNIT' => 'Unit sumber CS01', 'SOURCE_PARENT_CHAIN' => 'Relasi parent sumber ke CS01', 'SOURCE_ANCESTOR_CONTEXT' => 'Konteks ancestor sumber CS01'][$record['scope_basis']] }}</dd></div>
                            <div><dt>Registry keandalan</dt><dd>{{ $record['registered'] ? 'Terdaftar' : 'Belum terdaftar' }}</dd></div>
                        </dl>
                    @endif
                    <details class="technical-details"><summary>Identitas teknis & waktu record sumber</summary><dl class="detail-grid">@foreach(['canonical_id'=>'Canonical ID','source_updated_at'=>'Record sumber diperbarui','contract_version'=>'Versi kontrak'] as $field=>$label)<div><dt>{{ $label }}</dt><dd>{{ $record[$field] ?? 'Belum tersedia' }}</dd></div>@endforeach</dl><p class="data-note">Waktu record sumber bukan bukti kesegaran sinkronisasi.</p></details>
                    @unless($record['registered'])
                        <p class="data-note">Aset ini belum terdaftar di Registry keandalan. Riwayat WO dibaca dari inventaris tanpa pendaftaran otomatis. Operasi dan draft inspeksi tetap mengikuti Registry.</p>
                    @endunless
                </div>
                <aside class="asset-detail-sidebar" aria-label="Gambar dan menu Asset">
                    <x-asset-visual :asset-name="$record['description'] ?? $record['source_asset_number'] ?? $record['canonical_id']" :thumbnail="$illustration['path'] ?? null" :illustration-label="$illustration['label'] ?? null" />
                    <nav class="asset-detail-actions" aria-label="Menu Asset" id="asset-actions">
                        @canany(['write-pdm-activities','write-asset-disruptions','write-asset-priorities','write-inspection-drafts'])<h3 class="action-group-label">Catat & tindak lanjuti</h3>@endcanany
                        @can('write-pdm-activities')<a class="button primary" href="{{ route('pdm.create', ['asset_ref'=>$record['canonical_id']]) }}">+ Input pengukuran PdM</a>@endcan
                        @can('write-asset-disruptions')<a class="button secondary" href="{{ route('disruptions.create', ['asset_ref'=>$record['canonical_id']]) }}">Catat gangguan</a>@endcan
                        @can('write-asset-priorities')<a class="button secondary" href="{{ route('priorities.create', ['asset_ref'=>$record['canonical_id']]) }}">Prioritas perhatian aset</a>@endcan
                        @if($record['registered'])@can('write-inspection-drafts')<a class="button secondary" href="{{ route('inspections.create', ['asset_ref'=>$record['canonical_id']]) }}">Buat draft inspeksi untuk Asset ini →</a>@endcan @endif
                        <h3 class="action-group-label">Telusuri riwayat</h3>
                        <a class="button secondary" href="{{ route('work-orders.index', ['asset_ref'=>$record['canonical_id']]) }}">Lihat WO untuk Asset ini →</a>
                        <a class="button secondary" href="{{ route('assets.timeline', $record['canonical_id']) }}">Timeline aset →</a>
                        <a class="button secondary" href="{{ route('pdm.history', ['asset_ref'=>$record['canonical_id']]) }}">Riwayat PdM lokal →</a><a class="button secondary" href="{{ route('pdm.trends', ['asset_ref'=>$record['canonical_id']]) }}">Tren PdM per titik →</a>
                        <a class="button secondary" href="{{ route('work-orders.index', ['asset_ref'=>$record['canonical_id'], 'view'=>'disturbances']) }}">History gangguan · kandidat review →</a>
                        @if($record['registered'])<a class="button secondary" href="{{ route('operations', ['equipment'=>$record['canonical_id']]) }}">Buka konteks Operasi →</a>@endif
                    </nav>
                </aside>
            </div>
        </div>
        @if($draftMapping)
            <section class="panel detail-panel asset-mapping-note">
                <span class="draft-label">MAPPING BSR · DRAFT</span>
                <h2>{{ $draftMapping['engineering_group']['label'] }}</h2>
                <p class="muted">Inferensi engineering, bukan klasifikasi sumber. Pencocokan dokumen: {{ $draftMapping['mapping_state'] }}.</p>
                <a class="text-link" href="{{ route('assets.mapping', ['q'=>$record['source_asset_number']]) }}">Lihat fakta sumber dan kandidat dokumen →</a>
            </section>
        @endif
        <p class="data-note">Sumber: Reliability Mart melalui API Cockpit. Data ini tidak disalin ke database Laravel. Tanggal record sumber bukan bukti kesegaran sinkronisasi.</p>
    @endif
    <div id="log-gangguan">@include('disruptions.summary', ['summary'=>$disruptionSummary, 'assetRef'=>$asset])</div>
    <section class="panel disruption-history"><div class="detail-heading"><h2>Riwayat gangguan manual terbaru</h2><a class="text-link" href="{{ route('disruptions.index', ['asset_ref'=>$asset]) }}">Semua catatan →</a></div>@include('disruptions.table', ['events'=>$disruptionEvents, 'assetRef'=>$asset])</section>
</x-shell>

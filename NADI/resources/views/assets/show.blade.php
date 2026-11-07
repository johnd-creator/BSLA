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
        <div class="panel detail-panel">
            <div class="asset-detail-layout">
                <div class="asset-detail-facts">
                    <div class="detail-heading asset-detail-heading">
                        <div class="asset-heading-identity">
                            <p class="eyebrow">ASSET · {{ $record['site_code'] }} / {{ $record['organization_code'] }}</p>
                            <h2>{{ $record['source_asset_number'] ?? $record['canonical_id'] }}</h2>
                            <p>{{ $record['description'] ?? 'Deskripsi belum tersedia.' }}</p>
                            <span class="source-pill">Read only</span>
                        </div>
                    </div>
                    <section class="asset-reliability-status" aria-labelledby="asset-reliability-title">
                        <div class="asset-reliability-heading">
                            <h3 id="asset-reliability-title">Reliability score</h3>
                            <span class="asset-reliability-pending">Belum cukup data</span>
                        </div>
                        <p>Prioritas perhatian aset belum dinilai. Penilaian memerlukan:</p>
                        <ul class="asset-reliability-inputs">
                            <li>Kejadian gangguan yang sudah diverifikasi</li>
                            <li>Jam operasi dan availability dari historian</li>
                            <li>Riwayat pemeliharaan yang tervalidasi</li>
                            <li>Hasil PdM yang tervalidasi</li>
                        </ul>
                        <p class="asset-reliability-completeness">Kelengkapan data untuk score: <strong>Belum diverifikasi</strong>.</p>
                    </section>
                    <dl class="detail-grid">
                        @foreach(['canonical_id'=>'Canonical ID','status'=>'Status sumber','asset_type'=>'Tipe aset','plant'=>'Plant','unit'=>'Unit','location_ref'=>'Lokasi','parent_asset_ref'=>'Parent asset','source_updated_at'=>'Record sumber diperbarui','contract_version'=>'Versi kontrak'] as $field=>$label)
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
                    @unless($record['registered'])
                        <p class="data-note">Aset ini belum terdaftar di Registry keandalan. Riwayat WO dibaca dari inventaris tanpa pendaftaran otomatis. Operasi dan draft inspeksi tetap mengikuti Registry.</p>
                    @endunless
                </div>
                <aside class="asset-detail-sidebar" aria-label="Gambar dan menu Asset">
                    <x-asset-visual :asset-name="$record['description'] ?? $record['source_asset_number'] ?? $record['canonical_id']" :thumbnail="$illustration['path'] ?? null" :illustration-label="$illustration['label'] ?? null" />
                    <nav class="asset-detail-actions" aria-label="Menu Asset">
                        <a class="button secondary" href="{{ route('assets.timeline', $record['canonical_id']) }}">Timeline aset →</a>
                        <a class="button secondary" href="{{ route('pdm.history', ['asset_ref'=>$record['canonical_id']]) }}">Riwayat PdM lokal →</a>
                        @can('write-pdm-activities')
                            <a class="button secondary" href="{{ route('pdm.create', ['asset_ref'=>$record['canonical_id']]) }}">Input PdM untuk Asset ini →</a>
                        @endcan
                        @if($record['registered'])
                            <a class="button secondary" href="{{ route('operations', ['equipment'=>$record['canonical_id']]) }}">Buka konteks Operasi →</a>
                        @endif
                        <a class="button secondary" href="{{ route('work-orders.index', ['asset_ref'=>$record['canonical_id']]) }}">Lihat WO untuk Asset ini →</a>
                        <a class="button secondary" href="{{ route('work-orders.index', ['asset_ref'=>$record['canonical_id'], 'view'=>'disturbances']) }}">History gangguan · kandidat review →</a>
                        @if($record['registered'])
                            @can('write-inspection-drafts')
                                <a class="button secondary" href="{{ route('inspections.create', ['asset_ref'=>$record['canonical_id']]) }}">Buat draft inspeksi untuk Asset ini →</a>
                            @endcan
                        @endif
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
</x-shell>

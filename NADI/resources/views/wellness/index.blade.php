<x-shell title="Asset Wellness" eyebrow="DRAFT AWAL · UNTUK DISKUSI ENGINEER">
    <section class="panel wellness-intro">
        <div><span class="draft-label">Metode belum disahkan</span><h2>Kondisi aset, dengan bukti yang bisa ditelusuri</h2>
        @if($period->annual)<p>PdM 45% · Operasi 25% · Failure tervalidasi 20% · Pemeliharaan 10%. <strong>Bobot ilustratif</strong>, akan direvisi bersama engineer.</p>@else<p>Bobot, usulan normalisasi, batas kondisi dan bukti wajib dicatat engineer untuk rentang exact ini. Tidak ada bobot default yang dianggap benar.</p>@endif</div>
        <p class="data-note">Data kosong bukan 100. Cakupan dan confidence bukan skor kesehatan. Hasil pilot maupun approval KPI Reliability tidak menjadi pengesahan Wellness.</p>
    </section>
    <form class="panel wellness-filters" method="get" action="{{ route('wellness.index') }}">
        <label>Asset exact <input name="asset_ref" maxlength="240" value="{{ old('asset_ref', $assetRef) }}" placeholder="asset:MAXIMO:MXASSET:BSR:IP:…" required></label>
        @include('reliability.period-fields')
        <button class="button primary" type="submit">Tinjau bukti</button><a class="button secondary" href="{{ route('assets.index') }}">Pilih dari Master Asset</a>
    </form>
    @if(!$report)
        <section class="panel wellness-empty"><h2>Pilih aset untuk mulai</h2><p>Buka Master Asset → detail → Tinjau draft Wellness. Tidak ada skor contoh yang dicampur dengan data aset nyata.</p></section>
    @else
        <div class="wellness-heading"><div><h2>{{ $report['asset']['description'] ?? 'Identitas sumber belum dapat dibaca' }}</h2><p class="muted">{{ $report['asset']['source_asset_number'] ?? $assetRef }} · Bukti {{ $period->label() }} · Asia/Jakarta</p></div><a class="text-link" href="{{ route('assets.show', $assetRef) }}">Detail aset →</a></div>
        @if($report['asset'] === null)<p class="alert warning" role="status">Sumber aset tidak tersedia atau identitas belum terkonfirmasi. Bukti lokal tetap terlihat; ini bukan verifikasi aset.</p>@endif
        @if($report['attention_required'])
            <section class="panel wellness-alert" role="status"><h2>Perlu perhatian segera</h2><p>Engineer menetapkan prioritas <strong>Segera</strong>. Tindak lanjut ini tetap menonjol, terlepas dari rata-rata/skor apa pun.</p><p>{{ $report['priority']['observed_condition'] }}</p><a class="text-link" href="{{ route('priorities.show', $report['priority']['id']) }}">{{ $report['priority']['reference'] }} · versi {{ $report['priority']['version'] }} →</a></section>
        @endif
        <section class="panel wellness-summary" aria-labelledby="wellness-result">
            <div><p class="eyebrow">SKOR WELLNESS · DRAFT</p><h2 id="wellness-result">Belum cukup data</h2><p>Skor ditahan. Metode normalisasi, batas kondisi dan kelayakan bukti belum disepakati. Tidak ada kategori sehat atau nilai pengganti.</p></div>
            <dl><div><dt>Komponen layak diberi skor</dt><dd>0 dari 4 <small>Bukan persen kelengkapan data</small></dd></div><div><dt>Confidence penilaian</dt><dd>{{ $report['confidence'] }} <small>Bukan probabilitas aset sehat</small></dd></div><div><dt>Criticality aset</dt><dd>{{ $report['criticality'] }} <small>Konsekuensi kegagalan, terpisah dari kondisi</small></dd></div></dl>
        </section>
        <section class="panel wellness-priority"><h2>Prioritas perhatian engineer</h2>
            @if($report['priority'])<p><strong>{{ \App\Models\AssetPriority::URGENCIES[$report['priority']['urgency']] }}</strong> · {{ $report['priority']['reasoning'] }}</p><a class="text-link" href="{{ route('priorities.show', $report['priority']['id']) }}">Buka dasar prioritas →</a>
            @else<p>Belum ada prioritas aktif yang dicatat. Ini bukan pernyataan aman dan bukan bukti tidak ada kondisi kritis.</p>@endif
            <p class="data-note">Prioritas aktif tidak dibatasi periode bukti. Urgensi bukan criticality; keduanya tidak dimasukkan ke rata-rata Wellness. Deteksi kondisi kritis otomatis belum aktif tanpa threshold engineer.</p>
        </section>
        <p class="notice">Rekap historis memakai bukti dan review terkini. Ini bukan penilaian kondisi yang telah diketahui pada tanggal akhir periode. Prioritas aktif di bawah adalah kondisi terkini, bukan prioritas historis.</p>
        @include('wellness.policy-summary', ['report' => $report['method_draft']])
        <p><a class="button secondary" href="{{ route('wellness.policy', ['asset_ref'=>$assetRef, ...$period->query()]) }}">Tinjau / atur usulan metode →</a></p>
        @unless($period->annual)<p class="notice">Usulan metode Wellness tahunan tidak diterapkan otomatis ke rentang ini. Catat usulan per rentang; skor tetap ditahan sampai normalisasi dan kelayakan bukti disepakati.</p>@endunless
        @include('wellness.completeness', ['matrix' => $report['completeness']])
        <div class="wellness-components">
            @foreach($report['components'] as $key => $component)
                <section class="panel wellness-component" aria-labelledby="component-{{ $key }}">
                    <div class="wellness-component-heading"><h2 id="component-{{ $key }}">{{ $component['label'] }}</h2><span class="wellness-weight">{{ $component['weight'] === null ? 'Belum ditentukan' : $component['weight'].'%' }} <small>{{ $period->annual ? 'ilustratif' : 'usulan draft' }}</small></span></div>
                    <p class="wellness-pending">Skor belum tersedia</p>
                    @if($key === 'pdm')
                        <p><strong>{{ $component['evidence']['count'] }}</strong> pengukuran lokal pada periode ini. {{ $component['evidence']['quality']['current_analysis'] }} analisis sesuai versi pengukuran; {{ $component['evidence']['quality']['stale_analysis'] }} berubah sejak review; {{ $component['evidence']['quality']['unknown_analysis'] }} basis review tidak diketahui; {{ $component['evidence']['quality']['no_analysis'] }} belum dianalisis.</p>
                        @if($component['evidence']['truncated'])<p class="alert warning">Parsial: kualitas diperiksa hanya pada {{ $component['evidence']['inspected_count'] }} pengukuran terbaru. Tidak mewakili seluruh bukti.</p>@endif
                    @elseif($key === 'operations')
                        <p>Cakupan log manual: <strong>{{ $component['evidence']['coverage_percent'] === null ? 'Belum diketahui' : number_format($component['evidence']['coverage_percent'], 2).'%' }}</strong> dari periode terpilih. RUN terverifikasi: <strong>{{ $component['evidence']['operating_seconds'] === null ? 'Belum tersedia' : number_format($component['evidence']['operating_seconds'] / 3600, 2).' jam' }}</strong>.</p>
                        <p class="data-note">Log terakhir berakhir: {{ $component['evidence']['latest_ended_at'] ?? 'Belum tersedia' }}. {{ $component['evidence']['truncated'] ? 'Parsial: batas pembacaan log tercapai.' : '' }}</p>
                    @elseif($key === 'failure')
                        <p><strong>{{ $component['evidence']['reviewed_onset_count'] }}</strong> failure direview lokal dengan onset pasti di periode ini. Cakupan sensus: {{ ['UNKNOWN'=>'Belum diketahui','STALE'=>'Perlu review ulang','ATTESTED_LOCAL'=>'Pernyataan kelengkapan lokal'][$component['evidence']['coverage_status']] ?? 'Belum diketahui' }}.</p>
                        <p class="data-note">Kejadian terakhir: {{ $component['evidence']['latest_failure_at'] ?? 'Belum tersedia' }}. Review terakhir: {{ $component['evidence']['latest_reviewed_at'] ?? 'Belum tersedia' }}.</p>
                        <p class="data-note">{{ $component['evidence']['quality']['unreviewed'] }} belum direview · {{ $component['evidence']['quality']['stale'] }} stale · {{ $component['evidence']['quality']['uncertain'] }} belum pasti · {{ $component['evidence']['quality']['duplicate'] }} duplicate · {{ $component['evidence']['quality']['missing_failure_time'] }} onset kosong (kategori periode terpilih). {{ $component['evidence']['quality']['unknown_year'] }} observasi tanpa tahun diketahui. {{ count($component['evidence']['overlap_event_ids']) }} event dengan konflik interval di seluruh tahun yang dibaca.</p>
                        @if($component['evidence']['status'] === 'PARTIAL')<p class="alert warning">Parsial: batas 2.000 observasi tercapai. Jumlah bukan total bukti lengkap.</p>@endif
                    @else
                        <p>WO unik pada periode actual start terpilih: <strong>{{ $component['evidence']['work_order_count'] ?? 'Tidak tersedia' }}</strong>. {{ match($component['evidence']['status']) { 'UNAVAILABLE'=>'Sumber WO tidak tersedia, bukan nol.', 'RANGE_AGGREGATE_NOT_AVAILABLE'=>'Agregat WO rentang belum tersedia. Tidak diprorata dari angka tahunan.', default=>'Nol hanya berarti tidak ada WO tersimpan pada bucket tersebut.' } }}</p>
                        <p class="data-note">WO dengan tahun tidak diketahui (semua tahun): {{ $component['evidence']['all_year_counts']['unknown_date_work_order_count'] ?? 'Tidak tersedia' }}. Duplicate record tidak ditambahkan menjadi kejadian.</p>
                    @endif
                    <dl class="wellness-evidence"><div><dt>Cakupan</dt><dd>{{ $component['coverage'] }}</dd></div><div><dt>Kebaruan</dt><dd>{{ $component['freshness'] }}</dd></div><div><dt>Confidence bukti</dt><dd>{{ $component['confidence'] }}</dd></div></dl>
                    <details><summary>Apa yang perlu diputuskan engineer?</summary><p>{{ $component['blocker'] }}</p></details>
                    <a class="button secondary" href="{{ $component['url'] }}">Telusuri bukti {{ $component['label'] }} →</a>
                </section>
            @endforeach
        </div>
        <section class="panel wellness-trace"><h2>Jejak bukti yang ditampilkan</h2><p>Hingga 8 pengukuran dan 8 failure terbaru. Buka sumber untuk seluruh bukti, koreksi, pengecualian dan riwayat versi.</p>
            <div class="wellness-trace-grid"><div><h3>PdM</h3><ul>@forelse($report['components']['pdm']['evidence']['rows'] as $row)<li><a class="text-link" href="{{ route('pdm.show', $row['id']) }}">{{ $row['reference'] }} · v{{ $row['version'] }}</a><span>{{ $row['measurement'] }} · {{ $row['precision'] }}</span>@if($row['analysis_id'])<a class="text-link" href="{{ route('inspections.show', $row['analysis_id']) }}">Analisis terkait →</a>@endif</li>@empty<li>Belum ada pengukuran lokal di periode ini.</li>@endforelse</ul></div>
            <div><h3>Failure direview lokal</h3><ul>@forelse($report['components']['failure']['evidence']['rows'] as $row)<li><a class="text-link" href="{{ route('reliability.reviews', ['disruption'=>$row['event_id'], 'asset_ref'=>$assetRef]) }}">{{ $row['reference'] }} · v{{ $row['event_version'] }} · review {{ $row['review_revision'] }}</a><span>Onset {{ $row['failure_at'] }}</span></li>@empty<li>Belum ada failure dengan review terkini dan onset pasti di periode ini. Bukan bukti bebas failure.</li>@endforelse</ul></div></div>
            <details><summary>Versi metode dan batas laporan</summary><p>{{ $report['method_note'] }}</p><p>Versi draft: {{ $report['schema_version'] }}. Dibaca: {{ $report['observed_at'] }}.</p><p>{{ $report['trace_note'] }}</p><p class="wellness-hash">Basis bukti Reliability: {{ $report['reliability_evidence_hash'] }}</p><a class="text-link" href="{{ route('reliability.download', ['asset_ref'=>$assetRef, ...$period->query()]) }}">Unduh bukti Reliability saat ini (bukan snapshot Wellness) →</a></details>
        </section>
        <section class="panel wellness-method"><h2>Bahan revisi bersama engineer</h2><ol><li>Tentukan aset/titik, metode PdM, unit dan mode operasi yang wajib.</li><li>Sepakati batas kondisi dan aturan normalisasi, cakupan minimum, usia data serta confidence.</li><li>Rekonsiliasi failure per kejadian dan hubungan WO. Jangan menghukum satu failure dua kali lewat jumlah WO.</li><li>Uji pilot dengan data nyata. Sorot kondisi kritis tersendiri walau rata-rata tinggi; jangan menebak criticality.</li><li>Revisi bobot, lalu sepakati pengesahan metode dan hasil. Draft ini tidak memberi approval atau keputusan operasi.</li></ol></section>
    @endif
</x-shell>

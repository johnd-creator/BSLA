<section class="panel wellness-completeness" aria-labelledby="wellness-completeness-title">
    <div class="wellness-heading"><div><p class="eyebrow">KELENGKAPAN BUKTI · SAAT INI</p><h2 id="wellness-completeness-title">Matriks kelengkapan Asset Wellness</h2></div>@if($matrix['available'])<a class="button secondary" href="{{ route('pdm.plans.index', ['asset_ref' => $assetRef]) }}">Tinjau rencana PdM →</a>@endif</div>
    <p>Per {{ $matrix['observed_on'] }} · Asia/Jakarta. Titik wajib di sini berarti titik/konteks dalam <strong>rencana PdM lokal aktif</strong>, bukan pernyataan bahwa seluruh kebutuhan aset telah dipetakan. Rencana dijeda tidak masuk penyebut.</p>
    <p class="notice">Matriks saat ini tidak dibatasi periode laporan di atas dan bukan kepatuhan historis. Kelengkapan, kesegaran, analisis dan efektivitas ditampilkan terpisah; tidak menghasilkan skor kesehatan.</p>
    @if(!$matrix['available'])
        <p class="alert warning">Penyimpanan rencana PdM belum tersedia. Penyebut titik wajib belum dapat dibaca, bukan nol.</p>
    @elseif(!$matrix['required_count'])
        <p class="notice"><strong>Penyebut titik wajib belum ditentukan.</strong> Belum ada rencana PdM lokal aktif untuk aset ini. Pengukuran yang sudah ada tidak otomatis menjadi seluruh titik wajib. {{ $matrix['paused_count'] }} rencana dijeda.</p>
    @else
        <dl class="wellness-completeness-counts">
            <div><dt>Rencana aktif aset ini</dt><dd>{{ $matrix['required_count'] }} titik/konteks <small>{{ $matrix['paused_count'] }} dijeda, dikecualikan</small></dd></div>
            <div><dt>Bukti masih berlaku</dt><dd>{{ $matrix['counts']['current'] }} dari {{ $matrix['inspected_count'] }} baris diperiksa <small>Bukan persen kesehatan</small></dd></div>
            <div><dt>Celah bukti pada baris diperiksa</dt><dd>{{ $matrix['counts']['missing'] }} belum diukur · {{ $matrix['counts']['expired'] }} kedaluwarsa · {{ $matrix['counts']['unknown'] }} belum pasti</dd></div>
            <div><dt>Jadwal pada baris diperiksa</dt><dd>{{ $matrix['counts']['overdue'] }} terlambat · {{ $matrix['counts']['due'] }} jatuh tempo hari ini</dd></div>
        </dl>
        @if($matrix['truncated'])<p class="alert warning">Parsial: hanya {{ $matrix['inspected_count'] }} dari {{ $matrix['required_count'] }} rencana aktif diperiksa, diurutkan tanggal jatuh tempo pertama lalu ID. Ringkasan bukan seluruh aset. Buka rencana PdM untuk halaman berikutnya.</p>@endif
        <p class="data-note">Valid di sini berarti cocok persis dengan rencana, nilai terisi/finite dan bukan waktu masa depan; bukan sertifikasi alat atau diagnosis. Mengikuti jadwal existing, catatan kosong/tidak cocok dapat dilewati menuju bukti valid sebelumnya. Batas pencarian {{ \App\Services\PdmSchedule::LIMIT }} kandidat per rencana; tidak ada bukti di hasil terbatas berarti belum pasti.</p>
        <p class="data-note">Geser tabel ke samping pada layar kecil untuk melihat analisis dan tindak lanjut.</p>
        <div class="wellness-matrix-scroll" role="region" aria-label="Tabel kelengkapan titik PdM" tabindex="0">
            <table class="wellness-matrix"><caption>Titik/konteks wajib menurut rencana lokal aktif, dengan bukti terbaru yang memenuhi rencana</caption><thead><tr><th scope="col">Titik dan rencana</th><th scope="col">Pengukuran valid terakhir</th><th scope="col">Kesegaran dan jadwal</th><th scope="col">Analisis pengukuran</th><th scope="col">Tindak lanjut terkait</th></tr></thead><tbody>
            @foreach($matrix['rows'] as $row)
                <tr><th scope="row"><a class="text-link" href="{{ route('pdm.plans.show', $row['plan']) }}">{{ $row['plan']->point()['label'] ?? $row['plan']->point_key }} · {{ $row['plan']->unit ?? 'Satuan belum ditentukan' }}</a><span>{{ $row['plan']->reference() }} · v{{ $row['plan']->version }} · {{ $row['plan']->method }}</span><span>Setiap {{ $row['plan']->frequency_value }} {{ \App\Models\PdmInspectionPlan::FREQUENCIES[$row['plan']->frequency_unit] }}</span><details><summary>Konteks exact</summary><p>{{ $row['plan']->instrument }} · {{ $row['plan']->measurement_mode }} · {{ $row['plan']->operating_condition }}</p><p>{{ $row['plan']->asset_selection_note }}</p><p>Template {{ $row['plan']->template_id }}</p></details></th>
                <td>@if($row['measurement'])<a class="text-link" href="{{ route('pdm.show', $row['measurement']) }}">{{ $row['measurement']->reference() }} · v{{ $row['measurement']->version }}</a><span>{{ $row['measurement']->measurementLabel() }}</span><span>{{ $row['measurement']->precisionLabel() }}</span><strong>{{ $row['measurement']->readings[$row['plan']->point_key]['value'] }} {{ $row['plan']->unit }}</strong>@else{{ $row['state'] === 'unknown' ? 'Belum pasti: batas pencarian tercapai' : 'Belum ada bukti valid' }}@endif</td>
                <td><strong>{{ ['current' => 'Bukti masih berlaku', 'expired' => 'Bukti kedaluwarsa', 'missing' => 'Belum diukur', 'unknown' => 'Cakupan belum pasti'][$row['state']] }}</strong><span>{{ $row['schedule']['label'] }}</span><span>Jatuh tempo: {{ $row['schedule']['next_due_on']?->format('d M Y') ?? 'Belum pasti' }}</span></td>
                <td><strong>{{ ['current' => 'Analisis sesuai basis pengukuran', 'stale' => 'Analisis stale · tinjau ulang', 'unknown' => 'Basis analisis belum diketahui', 'missing' => 'Belum dianalisis'][$row['analysis_state']] }}</strong>@if($row['inspection'])<a class="text-link" href="{{ route('inspections.show', $row['inspection']) }}">{{ $row['inspection']->reference() }} →</a>@endif</td>
                <td>@if($row['follow_up'])<span>{{ \App\Models\InspectionDraft::FOLLOW_UP_STATUSES[$row['inspection']->follow_up_status] ?? 'Status belum dicatat' }}</span>@if($row['follow_up']['state'] !== 'unavailable')<a class="text-link" href="{{ route('inspections.effectiveness', $row['inspection']) }}">{{ $row['follow_up']['label'] }} →</a>@else<span>{{ $row['follow_up']['label'] }}</span>@endif
                @else
                    Belum ada rekomendasi tertaut pada pengukuran ini.
                @endif</td></tr>
            @endforeach
            </tbody></table>
        </div>
    @endif
    <h3>Bukti tindak lanjut aset</h3><p class="data-note">Rekomendasi lintas tanggal pada aset exact ini, termasuk dari pengukuran lebih lama atau tanpa tautan PdM. Tidak otomatis memenuhi titik rencana. Status Selesai bukan bukti efektif; keputusan tetap penilaian engineer dengan basis yang ditelusuri.</p>
    @if($matrix['follow_ups_truncated'])<p class="alert warning">Parsial: {{ count($matrix['follow_ups']) }} dari {{ $matrix['follow_up_count'] }} rekomendasi ditampilkan, menurut perubahan terakhir. <a class="text-link" href="{{ route('action-board') }}#follow-ups-title">Buka Action Board (seluruh aset) →</a></p>@endif
    <ul class="wellness-follow-ups">
    @forelse($matrix['follow_ups'] as $action)
        <li><a class="text-link" href="{{ route('inspections.show', $action['inspection']) }}">{{ $action['inspection']->reference() }} · v{{ $action['inspection']->version }}</a><p>{{ $action['inspection']->recommendation }}</p><p>{{ \App\Models\InspectionDraft::FOLLOW_UP_STATUSES[$action['inspection']->follow_up_status] ?? 'Status belum dicatat' }} · {{ $action['label'] }}</p>
        @if(in_array($action['analysis_state'], ['stale', 'unknown']))<p class="notice">{{ $action['analysis_state'] === 'stale' ? 'Analisis stale: pengukuran berubah sejak ditinjau.' : 'Basis review analisis belum diketahui.' }}</p>@elseif($action['analysis_state'] === 'unlinked')<p class="data-note">Tanpa tautan pengukuran PdM.</p>@endif
        @if($action['review'])<p>Tindakan dicatat {{ $action['review']->completed_on }}: {{ $action['review']->action_taken }}</p><p class="data-note">Review {{ $action['review']->revision }} · {{ $action['review']->created_at->setTimezone('Asia/Jakarta')->format('d M Y H:i') }} WIB</p>@endif
        @if($action['state'] !== 'unavailable')<a class="text-link" href="{{ route('inspections.effectiveness', $action['inspection']) }}">Telusuri bukti sebelum/sesudah dan riwayat review →</a>@endif</li>
    @empty<li>Belum ada rekomendasi lokal untuk aset ini. Ini bukan bukti bahwa tindak lanjut tidak diperlukan.</li>@endforelse
    </ul>
</section>

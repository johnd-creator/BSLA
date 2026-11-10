@php
    $scope = ['asset_ref' => $assetRef, ...$period->query()];
    $states = ['voided'=>'Dibatalkan', 'unreviewed'=>'Belum direview', 'stale'=>'Review kedaluwarsa', 'uncertain'=>'Belum dipastikan', 'failure'=>'Kehilangan fungsi · review lokal', 'not_failure'=>'Bukan failure aset ini', 'duplicate'=>'Duplikat'];
@endphp
<x-shell title="Intake bukti pilot" eyebrow="PANDUAN PER ASET / PERIODE · TANPA VERIFIKASI OTOMATIS">
    <a class="back-link" href="{{ route('reliability.index', $scope) }}">← Reliability</a>
    <section class="panel reliability-panel detail-panel">
        <h2>1. Tetapkan aset & periode</h2>
        <p>Mulai dari catatan asli untuk satu aset. Lengkapi bukti fungsi dan waktu, lalu rekonsiliasi melalui alur Reliability yang sama. Panduan ini tidak membuat skor, review, snapshot atau approval otomatis.</p>
        <form method="get" action="{{ route('reliability.intake') }}" class="form-grid">
            <div><label for="asset_ref">Canonical ID aset BSR / IP</label><input id="asset_ref" name="asset_ref" value="{{ $assetRef }}" maxlength="240" required placeholder="Salin identitas dari Master Asset"><x-field-error name="asset_ref" /><a class="text-link" href="{{ route('assets.index') }}">Cari di Master Asset</a></div>
            @include('reliability.period-fields')
            <div class="form-actions"><button class="button primary" type="submit">Buka panduan aset</button></div>
        </form>
    </section>
    @if($report)
    <section class="panel reliability-panel detail-panel">
        <h2>2. Temukan catatan asal</h2>
        <p><strong>{{ $report['asset']['description'] ?? $assetRef }}</strong> · {{ $period->label() }} · WIB</p>
        @if(!$report['asset'])<p class="notice">Identitas sumber belum tersedia. Bukti lokal tetap dapat dibaca; identitas baru tidak diverifikasi dari CSV.</p>@endif
        <ol><li>Catat nomor atau halaman log operator/laporan gangguan dan referensi bukti lapangan.</li><li>Pisahkan aset penyebab, terdampak dan peran belum diketahui. Satu kejadian dapat memiliki beberapa aset.</li><li>Periksa daftar di bawah sebelum membuat kejadian baru. Nomor WO yang sama tidak otomatis berarti duplikat.</li></ol>
        <div class="form-actions">@can('write-asset-disruptions')<a class="button primary" href="{{ route('disruptions.create', ['asset_ref'=>$assetRef]) }}">Catat observasi asli</a>@endcan<a class="button secondary" href="{{ route('disruptions.index', ['asset_ref'=>$assetRef]) }}">Semua log aset</a></div>
        <p class="data-note">Pembuatan observasi mencatat fakta kejadian, bukan menetapkan failure. Jika hanya tanggal diketahui, biarkan jam kosong.</p>
    </section>
    <section class="panel reliability-panel detail-panel" id="intake-events">
        <h2>3. Lengkapi fungsi, waktu & bukti</h2>
        <p>Gunakan <strong>Buka review terpandu</strong> untuk mencatat fungsi yang hilang, onset, kembali siap setelah pengujian, serta interval repair aktif dan jedanya. Waktu WO tidak disalin menjadi waktu repair.</p>
        <p class="data-note">Tanpa tanggal ditampilkan lebih dahulu, lalu periode dipilih dan periode lain. Daftar ini tidak menyembunyikan episode belum lengkap. Tanggal observasi hanya membantu antrean, bukan bukti onset.</p>
        @if($report['coverage']['local_rows_truncated'])<p class="notice error">Daftar parsial: batas 2.000 observasi tercapai. Ini bukan seluruh populasi.</p>@endif
        <p>{{ $events->firstItem() ?? 0 }}–{{ $events->lastItem() ?? 0 }} dari {{ $events->total() }} catatan lokal · 20 per halaman</p>
        <div class="table-wrap table-scroll"><table><thead><tr><th>Catatan / versi</th><th>Periode & status</th><th>Yang perlu diperiksa</th><th>Lanjutkan</th></tr></thead><tbody>
        @forelse($events as $row)
            <tr><td><a class="text-link" href="{{ route('disruptions.show', $row['event_id']) }}">{{ $row['reference'] }}</a><small>ID {{ $row['event_id'] }} · event_version {{ $row['event_version'] }} · review_revision {{ $row['review_revision'] ?? 0 }}</small></td><td>{{ $states[$row['state']] }}<small>{{ $row['date'] ?? 'Tanggal belum diketahui' }} · {{ $row['date'] === null ? 'Tanpa periode' : ($row['in_year'] ? 'Dalam periode pilihan' : 'Di luar periode pilihan') }}</small></td><td>
            @if(in_array($row['state'], ['unreviewed','stale','uncertain'], true))<p>Klasifikasi & referensi bukti perlu diperiksa.</p>@endif
            @if($row['state'] === 'failure')
                <ul><li>Fungsi: {{ $row['required_function'] ? 'tercatat' : 'belum dicatat' }}</li><li>Onset / kembali siap: {{ $row['failure_at'] && $row['restored_at'] ? 'kedua batas tercatat' : 'belum lengkap' }}</li><li>Repair: {{ \App\Models\ReliabilityReview::REPAIR_STATES[$row['repair_state']] ?? 'Belum diketahui' }}</li><li>Bukti waktu: {{ $row['timing_evidence'] ? 'tercatat, tetap perlu diperiksa' : 'belum dicatat' }}</li></ul>
            @endif
            @if(in_array($row['event_id'], $report['overlap_event_ids'], true))<strong>Interval konflik; rekonsiliasi tanpa menghapus histori.</strong>@endif
            @if(in_array($row['state'], ['duplicate','not_failure','voided'], true))<p>Pengecualian dipertahankan dalam jejak bukti.</p>@endif
            </td><td><a class="text-link" href="{{ route('reliability.reviews', [$row['event_id'], 'asset_ref'=>$assetRef, ...$period->query()]) }}">Buka review terpandu</a></td></tr>
        @empty<tr><td colspan="4">Belum ada observasi lokal. Mulai dari catatan asli; ini bukan bukti nol failure.</td></tr>@endforelse
        </tbody></table></div>{{ $events->links() }}
    </section>
    @can('write-asset-disruptions')
    <section class="panel reliability-panel detail-panel">
        <h2>Opsional: pratinjau CSV ke draft review</h2>
        <p>Untuk kejadian yang sudah tercatat dan milik Anda. CSV hanya membuka isian draft satu per satu. Tidak ada impor massal, simpan otomatis atau perubahan klasifikasi.</p>
        <details><summary>Format & batas CSV</summary><p>UTF-8, pemisah koma, maksimal 50 baris dan 64 KiB. Header harus sama urutannya dengan template. Kutip sel dengan koma atau baris baru. active_intervals_text memakai satu interval per baris: awal | akhir.</p><p>event_id adalah angka ID gangguan. event_version dan review_revision harus sama dengan daftar di atas; isi review_revision 0 bila belum ada review. repair_state: unknown, ongoing, completed, atau not_applicable. Timestamp wajib ISO-8601 lengkap dengan detik dan zona; biarkan kosong bila belum diketahui. Template tidak berisi contoh operasional.</p></details>
        <a class="text-link" href="{{ route('reliability.intake.template') }}">Unduh template header CSV</a>
        <form method="post" action="{{ route('reliability.intake.preview') }}" class="stack">@csrf
            @foreach($scope as $name=>$value)<input type="hidden" name="{{ $name }}" value="{{ $value }}">@endforeach
            <div><label for="csv_text">Tempel CSV dari catatan asli</label><textarea id="csv_text" name="csv_text" rows="7" maxlength="65536" required>{{ old('csv_text', request('csv_text', '')) }}</textarea><x-field-error name="csv_text" /><x-field-error name="draft" /></div>
            <div class="form-actions"><button class="button secondary" type="submit">Periksa tanpa menyimpan</button><a class="button secondary" href="{{ route('reliability.intake', $scope) }}">Bersihkan pratinjau</a></div>
        </form>
        @if($preview !== null)
            <h3>Hasil pratinjau · belum tersimpan</h3>
            <p>Validasi format bukan verifikasi kebenaran bukti. Pilih klasifikasi sendiri dan attest ulang di form review. Isi draft tidak dipertahankan setelah halaman ditutup; simpan file asal Anda.</p>
            @foreach($preview as $row)
            <div class="reliability-readiness-card">
                <h3>Baris data {{ $loop->iteration }} · kejadian {{ $row['values']['event_id'] }}</h3>
                <p>{{ $row['errors'] ? 'Perlu diperbaiki sebelum membuka draft' : 'Format diperiksa; bukti belum diverifikasi' }}</p>
                @if($row['errors'])<ul class="notice error">@foreach($row['errors'] as $error)<li>{{ $error }}</li>@endforeach</ul>@endif
                @if($row['warnings'])<ul>@foreach($row['warnings'] as $warning)<li>{{ $warning }}</li>@endforeach</ul>@endif
                <details><summary>Periksa isian baris</summary><dl class="detail-grid">@foreach($row['values'] as $name=>$value)<div><dt>{{ $name }}</dt><dd class="disruption-prose">{{ $value !== '' ? $value : 'Belum diisi' }}</dd></div>@endforeach</dl></details>
                @unless($row['errors'])<form method="post" action="{{ route('reliability.intake.draft') }}">@csrf
                    @foreach($scope as $name=>$value)<input type="hidden" name="{{ $name }}" value="{{ $value }}">@endforeach
                    @foreach($row['values'] as $name=>$value)<input type="hidden" name="draft[{{ $name }}]" value="{{ $value }}">@endforeach
                    <button class="button secondary" type="submit">Buka draft untuk diperiksa</button>
                </form>@endunless
            </div>
            @endforeach
        @endif
    </section>
    @endcan
    <section class="panel reliability-panel detail-panel">
        <h2>4. Rekonsiliasi sebelum snapshot</h2>
        <ol><li>Periksa episode unik, non-failure, duplikat, recurrence/reopen, catatan kedaluwarsa dan interval konflik.</li><li>Jangan singkirkan episode dengan batas waktu belum lengkap. Cakupan beberapa sampel bukan kelengkapan populasi.</li><li>Tetapkan metode untuk aset/periode exact ini. Restoration dan active repair memiliki kebutuhan bukti berbeda.</li><li>Periksa readiness dan jejak pembilang/penyebut, baru simpan snapshot melalui halaman Reliability. Supervisor mengesahkan secara terpisah.</li></ol>
        <div class="form-actions"><a class="button primary" href="{{ route('reliability.index', $scope) }}#reliability-review-queue">Periksa rekonsiliasi & snapshot</a><a class="button secondary" href="{{ route('reliability.policies', $scope) }}">Metode periode ini</a><a class="button secondary" href="{{ route('reliability.operating.index', $scope) }}">Bukti operasi manual</a></div>
        <p class="data-note">Historian bukan syarat wajib MTTR. MTBF tetap memerlukan exposure terverifikasi. Belum ada data bukan nilai nol atau bukti aset sehat.</p>
    </section>
    @endif
</x-shell>

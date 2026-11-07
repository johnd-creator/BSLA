<x-shell :title="$mode === 'disturbances' ? 'History gangguan' : 'Riwayat Work Order'" eyebrow="MASTER ASSET · RELIABILITY MART">
    <a class="back-link" href="{{ $asset ? route('assets.show', $asset['canonical_id']) : route('assets.index') }}">← {{ $asset ? 'Detail Asset' : 'Master Asset' }}</a>
    @if($asset)
        <div class="panel history-context"><div><strong>{{ $asset['source_asset_number'] ?? $asset['canonical_id'] }}</strong><p class="muted">{{ $asset['description'] ?? 'Deskripsi aset belum tersedia' }} · {{ $asset['unit'] ?? 'Unit belum tersedia' }}</p></div><span class="source-pill">BSR / IP · {{ $inventory ? 'Inventaris · non-Registry' : 'Registry' }}</span></div>
    @elseif(!request('asset_ref'))
        <p class="section-intro muted">Seluruh WO dalam Registry BSR/IP. Klik Asset untuk membuka riwayat khusus aset tersebut.</p>
    @endif
    @if($asset) @include('work-orders.annual') @endif
    <nav class="history-tabs" aria-label="Jenis riwayat">
        @foreach(['work-orders' => 'Riwayat WO', 'disturbances' => 'History gangguan'] as $view => $label)
            <a @class(['button', 'small', 'primary' => $mode === $view, 'secondary' => $mode !== $view]) @if($mode === $view) aria-current="true" @endif href="{{ route('work-orders.index', array_merge(request()->only(['asset_ref', 'status', 'from', 'to', 'year', 'sort', 'offset']), ['view' => $view])) }}">{{ $label }}</a>
        @endforeach
    </nav>
    @if($mode === 'disturbances')
        <section class="panel history-boundary" aria-labelledby="review-title"><h2 id="review-title">Kandidat review, belum kejadian tervalidasi</h2><p class="muted">Identitas kejadian, relasi parent/child dan multi-WO belum tersedia pada API ini. Daftar tetap menampilkan semua WO agar unknown tidak hilang. Satu WO bukan satu gangguan; frekuensi gangguan, Pareto, MTBF dan MTTR belum dihitung.</p></section>
    @endif
    @if(request('year'))<p class="annual-wo-filter"><strong>{{ request('year') === 'unknown' ? 'Tahun mulai belum diketahui' : 'Tahun mulai '.request('year').' · WIB' }}</strong> · <a class="text-link" href="{{ route('work-orders.index', ['asset_ref' => request('asset_ref'), 'view' => $mode]) }}">Lihat seluruh tahun</a></p>@endif
    <form class="panel filters history-filters" method="get">
        @if(request('asset_ref'))<input type="hidden" name="asset_ref" value="{{ request('asset_ref') }}">@endif
        <input type="hidden" name="view" value="{{ $mode }}">
        <div><label for="status">Status sumber</label><select id="status" name="status"><option value="">Semua status</option>@foreach(array_unique(array_filter(['CLOSE', 'COMP', 'WDONE', 'WAPPR', 'APPR', 'INPRG', 'CAN', 'CANCEL', request('status')])) as $value)<option value="{{ $value }}" @selected(request('status') === $value)>{{ $value }}</option>@endforeach</select></div>
        @if(request('year'))<input type="hidden" name="year" value="{{ request('year') }}">@else
        <div><label for="from">Dari tanggal · WIB</label><input id="from" name="from" type="date" value="{{ request('from') }}"></div>
        <div><label for="to">Sampai tanggal · WIB</label><input id="to" name="to" type="date" value="{{ request('to') }}"></div>
        @endif
        <div><label for="sort">Urutan record</label><select id="sort" name="sort"><option value="date_desc" @selected(request('sort', 'date_desc') === 'date_desc')>Terbaru dahulu</option><option value="date_asc" @selected(request('sort') === 'date_asc')>Terlama dahulu</option></select></div>
        <button type="submit" class="button primary">Terapkan</button>@if(request()->anyFilled(['status','from','to','sort']))<a class="text-link" href="{{ route('work-orders.index', ['asset_ref' => request('asset_ref'), 'view' => $mode, 'year' => request('year')]) }}">Reset</a>@endif
    </form>
    <x-active-filters :filters="['status'=>'Status','from'=>'Dari tanggal','to'=>'Sampai tanggal']" />
    @if(request('year'))<p class="history-date-note muted">Daftar mengikuti kelompok tahun actual start WIB dan hanya identitas WO unik. Untuk tahun belum diketahui, tanggal perubahan record hanya dipakai mengurutkan daftar, bukan menentukan tahun.</p>@else
    <p class="history-date-note muted">Filter dan urutan memakai actual start WO; jika kosong, tanggal perubahan record. Ini bukan tanggal kejadian gangguan. Tanggal pada tabel mempertahankan zona waktu sumber. Kosongkan periode untuk menyertakan record tanpa tanggal.</p>
    @endif
    @if($page === null && $inventoryUnavailable)
        <div class="panel connection-state"><h2>Riwayat WO inventaris belum tersedia</h2><p>Jalur baca WO untuk inventaris belum aktif atau aset tidak lagi termasuk cakupannya. Ini bukan hasil nol WO. Aset tidak didaftarkan otomatis ke Registry.</p></div>
    @elseif($page === null)
        <div class="panel connection-state"><h2>Riwayat belum terhubung</h2><p>Identitas aset atau respons Work Order belum dapat diverifikasi. Tidak ada data pengganti.</p></div>
    @else
        @if($mode === 'disturbances')
            <dl class="history-review-summary">
                <div><dt>Kandidat review</dt><dd>{{ $summary['candidate'] }} <small>WO di halaman ini</small></dd></div>
                <div><dt>Pemeliharaan terklasifikasi</dt><dd>{{ $summary['maintenance'] }} <small>WO di halaman ini</small></dd></div>
                <div><dt>Unknown</dt><dd>{{ $summary['unknown'] }} <small>WO di halaman ini</small></dd></div>
                <div><dt>Kejadian tervalidasi</dt><dd>— <small>Data belum tersedia</small></dd></div>
            </dl>
        @endif
        <div class="panel"><div class="panel-heading"><h2>Record WO <span class="count">{{ number_format($page['meta']['total'], 0, ',', '.') }}</span></h2><span class="muted">Sesuai filter · bukan jumlah gangguan</span></div>
            <div class="table-scroll record-scroll" role="region" tabindex="0" aria-label="Tabel data, dapat digeser"><table class="history-table"><thead><tr><th>WO / deskripsi</th>@unless($asset)<th>Asset</th>@endunless<th>Status / tipe</th><th>Tanggal acuan record</th><th>{{ $mode === 'disturbances' ? 'Bukti dan klasifikasi review' : 'Durasi pelaksanaan WO' }}</th></tr></thead><tbody>
                @forelse($page['items'] as $wo)
                    @php($interval = \App\Services\WorkOrderTiming::fromRecord($wo))
                    <tr><td class="history-description">@if($wo['work_order_id'])<a class="text-link" href="{{ route('work-orders.show', ['ref' => $wo['work_order_id'], 'event' => $wo['canonical_id'], ...request()->only(['asset_ref', 'view', 'status', 'from', 'to', 'year', 'sort', 'offset'])]) }}">{{ $wo['work_order_number'] ?? $wo['work_order_id'] }}</a>@else Referensi WO belum tersedia @endif<small>{{ $wo['description'] ?: 'Deskripsi belum tersedia' }}</small></td>
                    @unless($asset)<td><a class="text-link" href="{{ route('work-orders.index', ['asset_ref' => $wo['equipment_id'], 'view' => $mode]) }}">{{ $wo['asset_number'] ?? $wo['equipment_id'] }}</a></td>@endunless
                    <td><span class="badge neutral">{{ $wo['status'] ?? 'Unknown' }}</span><small>{{ $wo['evidence']['work_type'] }} · {{ $wo['evidence']['work_label'] }}</small>@if($wo['status'] === 'WAPPR')<small class="muted">Menunggu persetujuan</small>@endif</td>
                    <td class="wo-time">{{ $wo['evidence']['date'] ?? 'Belum tersedia' }}<small class="muted">{{ $wo['evidence']['date_basis'] }}</small></td>
                    <td>@if($mode === 'disturbances')<strong>{{ $wo['evidence']['label'] }}</strong><small>{{ $wo['evidence']['reason'] }}</small>@if($wo['failure_code'])<small>Failure code: {{ $wo['failure_code'] }}</small>@endif @else @if($interval['duration_hours'] !== null){{ number_format($interval['duration_hours'], 2) }} jam @else<span class="muted">Belum dihitung</span>@endif<small class="muted">{{ $interval['message'] }}</small>@endif</td></tr>
                @empty<tr><td colspan="{{ $asset ? 4 : 5 }}" class="empty-table">Tidak ada record WO pada filter ini. Ini tidak membuktikan aset tidak pernah mengalami gangguan.</td></tr>@endforelse
            </tbody></table></div>
            <div class="page-controls"><span class="muted">{{ $page['meta']['total'] ? $page['meta']['offset'] + 1 : 0 }}–{{ $page['meta']['offset'] + count($page['items']) }} dari {{ number_format($page['meta']['total'], 0, ',', '.') }} record · 25 per halaman</span><div>@if($page['meta']['offset'] > 0)<a class="button secondary small" href="{{ route('work-orders.index', array_merge(request()->only(['asset_ref', 'status', 'view', 'from', 'to', 'year', 'sort']), ['offset' => max(0, $page['meta']['offset'] - 25)])) }}">← Sebelumnya</a>@endif @if($page['meta']['has_more'])<a class="button secondary small" href="{{ route('work-orders.index', array_merge(request()->only(['asset_ref', 'status', 'view', 'from', 'to', 'year', 'sort']), ['offset' => $page['meta']['offset'] + 25])) }}">Berikutnya →</a>@endif</div></div>
        </div>
    @endif
    <details class="panel history-rules"><summary>Aturan baca dan batas data</summary><ul><li>Tipe CM/REPAIR/EMERGENCY kanonis atau failure code hanya menjadi kandidat review. Kode mentah yang belum dipetakan, termasuk CD, tetap unknown. PM/inspeksi/kalibrasi tidak otomatis gangguan, juga tidak membuktikan tidak ada gangguan.</li><li>WAPPR tetap backlog. CLOSE, WDONE, CAN atau CANCEL tidak membuktikan terjadi/tidaknya gangguan. Deskripsi tidak dipakai untuk menebak klasifikasi.</li><li>Record WO ditautkan dengan identitas persis. Identitas duplikat dalam satu respons ditolak. Parent/child dan beberapa WO untuk satu kejadian belum digabung; tidak ada penghitungan kejadian.</li><li>Durasi final hanya untuk CLOSE dengan dua actual timestamp valid. Actual start–finish bukan downtime, MTTR, atau jam tenaga kerja.</li><li>Data hanya dari Mart lokal dalam {{ $inventory ? 'inventaris hierarki CS01 BSR/IP untuk aset ini' : 'Registry BSR/IP' }}. Kelengkapan sejarah dan kesegaran sinkronisasi belum dibuktikan; hasil kosong bukan pernyataan aset sehat.</li></ul></details>
</x-shell>

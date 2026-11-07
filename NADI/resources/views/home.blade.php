<x-shell title="Beranda">
    @include('overview.navigation')
    <div class="overview-heading"><div><h2>Ringkasan workspace</h2><p class="muted">Angka sesuai cakupan masing-masing sumber. Data belum tersedia ditampilkan sebagai tanda pisah.</p></div><div class="page-actions">@can('write-pdm-activities')<a class="button primary" href="{{ route('pdm.create') }}">+ Input pengukuran</a>@endcan<a class="button secondary" href="{{ route('reports.index') }}">Buka laporan</a></div></div>
    @include('overview.metrics')
    <form class="panel home-filters" method="get" action="{{ route('home') }}" aria-label="Filter beranda">
        <div><label for="feed-scope">Cakupan panel</label><select id="feed-scope" name="scope">@foreach(['all'=>'Semua cakupan', 'local'=>'Catatan lokal', 'registry'=>'WO Registry BSR / IP'] as $value=>$label)<option value="{{ $value }}" @selected(($filters['scope'] ?? 'all') === $value)>{{ $label }}</option>@endforeach</select></div>
        <details class="mobile-filter-options" data-mobile-filters data-active="{{ collect(request()->only(['freshness','activity_type','period']))->contains(fn ($value) => $value && $value !== 'all') ? 'true' : 'false' }}" open><summary>Filter kesegaran & aktivitas <span aria-hidden="true">⌄</span></summary><div class="mobile-filter-options-fields"><div><label for="feed-freshness">Bukti kesegaran</label><select id="feed-freshness" name="freshness">@foreach(['all'=>'Semua bukti', 'recorded'=>'Waktu rekam lokal tersedia', 'unknown'=>'Sinkronisasi sumber belum diketahui'] as $value=>$label)<option value="{{ $value }}" @selected(($filters['freshness'] ?? 'all') === $value)>{{ $label }}</option>@endforeach</select></div>
        <div><label for="feed-type">Jenis aktivitas</label><select id="feed-type" name="activity_type">@foreach(\App\Services\HomeFeed::TYPES as $value=>$label)<option value="{{ $value }}" @selected(($filters['activity_type'] ?? 'all') === $value)>{{ $label }}</option>@endforeach</select></div>
        <div><label for="feed-period">Waktu aktivitas</label><select id="feed-period" name="period">@foreach(['all'=>'Semua waktu', '7'=>'7 hari terakhir', '30'=>'30 hari terakhir', '90'=>'90 hari terakhir'] as $value=>$label)<option value="{{ $value }}" @selected(($filters['period'] ?? 'all') === (string) $value)>{{ $label }}</option>@endforeach</select></div>
        </div></details><button class="button primary">Terapkan</button>@if(collect(request()->only(['scope','freshness','activity_type','period']))->contains(fn ($value) => $value && $value !== 'all'))<a class="text-link" href="{{ route('home') }}">Reset</a>@endif
        <details class="home-filter-note method-note"><summary>Cara kerja filter & kesegaran sumber</summary><p>Jenis dan waktu hanya memfilter Aktivitas terbaru. Cakupan dan bukti kesegaran memfilter panel kerja; metrik atas tetap global. Waktu rekam lokal bukan kondisi realtime. Tidak ada sumber yang dinyatakan segar tanpa bukti sinkronisasi.</p></details>
    </form>
    <div class="home-grid">
        <div class="home-column">
<section class="panel overview-panel home-attention" aria-labelledby="home-attention-title">
            <div class="overview-panel-heading"><h2 id="home-attention-title"><x-card-motif variant="inspection" class="card-motif--mark" />Perlu perhatian</h2><a href="{{ route('action-board') }}#priorities-title">Action Board →</a></div>
            <p class="muted">Urgensi yang dinilai engineer, lalu tanggal target / review terdekat. Bukan skor otomatis.</p>
            @if(!$feed['local'])<p class="home-empty">Penilaian dan tenggat lokal tidak termasuk filter ini.</p>
            @else
                @if($feed['priorities'] === null)<p class="home-empty">Penilaian belum tersedia. Kondisi aset tidak dapat disimpulkan.</p>
                @else
                    <ul class="home-list">@forelse($feed['priorities'] as $priority)<li>
                        <div class="home-row-title"><a href="{{ route('priorities.show', $priority) }}">{{ \Illuminate\Support\Str::afterLast($priority->asset_ref, ':') }}</a><span class="priority-urgency urgency-{{ $priority->urgency }}">{{ \App\Models\AssetPriority::URGENCIES[$priority->urgency] }}</span></div>
                        <p>{{ \Illuminate\Support\Str::limit($priority->reasoning, 150) }}</p>
                        <p class="home-meta">PIC {{ $priority->owner }} · Penilai {{ $priority->author?->name ?? 'Belum tersedia' }}</p>
                        <div class="home-deadlines">@foreach(['due_on'=>'Target', 'review_on'=>'Review'] as $field=>$label)<span @class(['attention-overdue'=>$priority->$field?->isBefore(today())])>{{ $label }}: {{ $priority->$field?->format('d M Y') ?? 'Belum ditetapkan' }}{{ $priority->$field?->isBefore(today()) ? ' · lewat' : '' }}</span>@endforeach</div>
                    </li>@empty<li class="home-empty">Belum ada prioritas aktif yang dinilai. Daftar kosong bukan berarti aset sehat atau risikonya rendah.</li>@endforelse</ul>
                @endif
                <h3 class="home-subtitle">Tenggat rekomendasi</h3>
                @if($feed['followUps'] === null)<p class="home-empty">Tenggat rekomendasi belum dapat dibaca.</p>@else
                    <ul class="home-list home-list-compact">@forelse($feed['followUps'] as $draft)<li><a href="{{ route('inspections.show', $draft) }}">{{ $draft->reference() }}</a><p class="home-meta">{{ $draft->asset_ref ? \Illuminate\Support\Str::afterLast($draft->asset_ref, ':') : 'Aset belum ditautkan' }} · {{ \App\Models\InspectionDraft::FOLLOW_UP_STATUSES[$draft->follow_up_status] }}</p><span @class(['attention-overdue'=>$draft->target_completion->isBefore(today())])>Target {{ $draft->target_completion->format('d M Y') }}{{ $draft->target_completion->isBefore(today()) ? ' · lewat' : '' }}</span></li>@empty<li class="home-empty">Tidak ada rekomendasi terbuka dengan target sampai 7 hari ke depan pada catatan tersedia.</li>@endforelse</ul>
                @endif
                <details class="method-note overview-note"><summary>Cakupan & aturan baca</summary><p>Maks. 6 penilaian aktif dan 4 tenggat. Tenggat bukan urgensi atau risiko yang sudah dinilai. <a href="{{ route('action-board') }}#follow-ups-title">Semua tindak lanjut →</a></p></details>
            @endif
        </section>
<section class="panel overview-panel home-candidates" aria-labelledby="home-candidates-title">
            <div class="overview-panel-heading"><h2 id="home-candidates-title"><x-card-motif variant="inventory" class="card-motif--mark" />Kandidat untuk ditinjau</h2><a href="{{ route('action-board') }}#candidates-title">Semua kandidat →</a></div>
            <p class="muted">Petunjuk yang belum memiliki penilaian. Bukan diagnosis, gangguan aktif, atau urutan risiko.</p>
            @if($feed['local'])
                <h3 class="home-subtitle">Log manual & rekomendasi tertunda</h3>
                @if($feed['candidates'] === null)<p class="home-empty">Kandidat lokal belum tersedia.</p>@else
                    <ul class="home-list home-list-compact">@forelse($feed['candidates'] as $candidate)<li><a href="{{ route('assets.show', $candidate->asset_ref) }}">{{ \Illuminate\Support\Str::afterLast($candidate->asset_ref, ':') }}</a><p>@if($candidate->disruption_count){{ $candidate->disruption_count }} log gangguan manual @endif @if($candidate->pdm_count) · {{ $candidate->pdm_count }} rekomendasi belum selesai @endif</p><a class="home-meta" href="{{ route('assets.show', $candidate->asset_ref) }}">Buka aset & bukti →</a></li>@empty<li class="home-empty">Belum ada kandidat lokal yang belum dinilai. Bukan konfirmasi kondisi sehat.</li>@endforelse</ul>
                @endif
                <p class="home-meta">Maks. 5 aset, urutan ID; seluruh tanggal catatan lokal, termasuk non-Registry. Log dibatalkan / rekomendasi selesai dikecualikan.</p>
            @endif
            @if($feed['registry'])
                <h3 class="home-subtitle">WO berulang · Registry BSR / IP</h3>
                @if($feed['repeat'] === null)<p class="home-empty">Sumber kandidat WO belum tersedia atau belum terverifikasi. Jumlah tidak diketahui, bukan nol.</p>@else
                    <p class="home-meta">{{ $feed['repeat']['coverage']['availability'] === 'PARTIAL' ? 'Bukti parsial' : 'Bukti tersedia dalam cakupan terbatas' }} · 90 hari · hanya halaman pertama, maks. 10 aset sebelum pencocokan penilaian.</p>
                    <ul class="home-list home-list-compact">@forelse(array_slice($feed['repeat']['unassessed'], 0, 5) as $candidate)<li><a href="{{ route('assets.show', $candidate['asset_ref']) }}">{{ $candidate['source_asset_number'] }}</a><p>{{ $candidate['event_count'] }} identitas WO CLOSE · kandidat review</p><a class="home-meta" href="{{ route('work-orders.index', ['asset_ref'=>$candidate['asset_ref'], 'status'=>'CLOSE', 'from'=>\Carbon\CarbonImmutable::parse($feed['repeat']['window']['start'])->setTimezone('Asia/Jakarta')->format('Y-m-d'), 'to'=>\Carbon\CarbonImmutable::parse($feed['repeat']['window']['as_of'])->setTimezone('Asia/Jakarta')->format('Y-m-d')]) }}">Telusuri WO →</a></li>@empty<li class="home-empty">Tidak ada kandidat belum dinilai pada cuplikan ini. Periksa Action Board untuk halaman lainnya.</li>@endforelse</ul>
                    <p class="home-meta">Bukti belum diketahui: waktu mulai {{ $feed['repeat']['coverage']['unknown_start_work_orders'] }}, task {{ $feed['repeat']['coverage']['unknown_task_work_orders'] }}, status {{ $feed['repeat']['coverage']['unknown_status_work_orders'] }}. Kelompok dapat tumpang tindih.</p>
                @endif
                <details class="method-note overview-note"><summary>Cakupan & aturan baca</summary><p>WO berulang bukan failure berulang. Non-task dan actual start harus terverifikasi, tanpa pengganti tanggal. Cakupan Registry tidak meliputi semua Master Asset; sinkronisasi sumber belum diketahui. Aset yang sama dapat muncul pada kedua sumber, jangan dijumlahkan.</p></details>
            @endif
            @if(!$feed['local'] && !$feed['registry'])<p class="home-empty">Tidak ada sumber yang cocok dengan kombinasi cakupan dan bukti kesegaran ini. <a href="{{ route('home') }}">Reset filter</a>.</p>@endif
        </section>
        </div>
        <div class="home-column">
<section class="panel overview-panel home-activity" aria-labelledby="home-activity-title">
            <div class="overview-panel-heading"><h2 id="home-activity-title"><x-card-motif variant="records" class="card-motif--mark" />Aktivitas terbaru</h2><span class="badge neutral">Tercatat lokal</span></div>
            <p class="muted">Waktu simpan / koreksi, bukan waktu gangguan atau pengukuran. Pelaku dan waktu sesuai jejak tersimpan.</p>
            @if(!$feed['local'])<p class="home-empty">Feed perubahan tersedia untuk catatan lokal. Riwayat perubahan WO sumber belum tersedia di feed ini.</p>
            @elseif($feed['activities'] === null)<p class="home-empty">Riwayat aktivitas belum dapat dibaca. Ini bukan berarti tidak ada aktivitas.</p>
            @else
                <ol class="home-list home-events">@forelse($feed['activities'] as $event)<li data-activity-kind="{{ $event['kind'] }}">
                    <div class="home-row-title"><a href="{{ $event['url'] }}">{{ $event['title'] }}</a><time datetime="{{ $event['at']->toIso8601String() }}">{{ $event['at']->format('d M Y H:i:s') }} UTC</time></div>
                    <p class="home-meta">{{ $event['actor'] }} · {{ $event['reference'] }} · v{{ $event['version'] }}@if($event['asset_ref']) · {{ \Illuminate\Support\Str::afterLast($event['asset_ref'], ':') }}@endif</p>
                    @if($event['detail'])<p>{{ $event['detail'] }}</p>@endif
                    @if($event['legacy'])<p class="home-meta">Metadata pembuatan lama; isi awal dan perubahan sebelumnya tidak direkonstruksi. Tautan membuka draft terkini.</p>@endif
                </li>@empty<li class="home-empty">Tidak ada aktivitas tercatat pada jenis dan waktu ini. Bukan konfirmasi tidak ada perubahan di sumber lain.</li>@endforelse</ol>
                <div class="pagination">{{ $feed['activities']->fragment('home-activity-title')->links() }}</div>
                @if(($filters['activity_page'] ?? 1) >= 100)<p class="home-meta">Batas cuplikan 100 halaman tercapai. Persempit jenis / waktu atau buka logbook sumber.</p>@endif
            @endif
            <details class="method-note overview-note"><summary>Cakupan & aturan baca</summary><p>Revisi gangguan / prioritas memakai jejak yang sudah tersimpan. Perubahan PdM, rekomendasi dan status dicatat mulai fitur ini aktif; riwayat lama tidak dibuat ulang dari tanggal pembaruan.</p></details>
        </section>
<section class="panel overview-panel home-quality" aria-labelledby="home-quality-title">
            <div class="overview-panel-heading"><h2 id="home-quality-title"><x-card-motif variant="measurement" class="card-motif--mark" />Kualitas data</h2><a href="{{ route('data-quality') }}">Detail kualitas →</a></div>
            <dl class="home-source-states">
                <div><dt>Inventaris · CS01</dt><dd>@if($snapshot['inventory'] === null)Belum tersedia @else{{ $snapshot['inventory']['complete'] ? 'Lengkap saat scan' : 'Cakupan masih parsial' }}<small>{{ number_format($snapshot['inventory']['pending_projection'], 0, ',', '.') }} menunggu proyeksi · {{ number_format($snapshot['inventory']['unknown'], 0, ',', '.') }} belum dikategorikan</small>@endif</dd></div>
                <div><dt>Backlog WAPPR · Registry</dt><dd>{{ $snapshot['metrics'][1]['value'] === null ? 'Belum tersedia' : 'Respons tersedia · bukan gangguan' }}</dd></div>
                <div><dt>PdM / rekomendasi lokal</dt><dd>{{ $snapshot['metrics'][2]['value'] === null || $snapshot['metrics'][3]['value'] === null ? 'Sebagian belum tersedia' : 'Draft lokal tersedia' }}<small>Dapat saling terkait, bukan total inspeksi unik.</small></dd></div>
                <div><dt>Kesegaran sumber</dt><dd>Belum dapat dipastikan<small>Waktu baca dan tanggal scan bukan jaminan data realtime.</small></dd></div>
            </dl>
            <details class="method-note overview-note"><summary>Cakupan & aturan baca</summary><p>Data kosong / belum tersedia bukan aman, sehat, nol risiko, atau nol gangguan. Skor kesehatan dan kondisi realtime belum dinilai.</p></details>
            <div class="home-shortcuts"><a href="{{ route('assets.index') }}">Master Asset</a><a href="{{ route('pdm.index') }}">Logbook PdM</a><a href="{{ route('disruptions.index') }}">Log gangguan</a></div>
        </section>
        </div>
    </div>
    <p class="overview-footnote">Dibaca <time datetime="{{ $snapshot['observed_at'] }}">{{ $snapshot['observed_at'] }}</time> · Bukan waktu sinkronisasi sumber. Muat ulang halaman untuk membaca ulang.</p>
</x-shell>

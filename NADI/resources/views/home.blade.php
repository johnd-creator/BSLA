<x-shell title="Beranda">
    @include('overview.navigation')
    <div class="overview-heading"><div><h2>Ringkasan workspace</h2><p class="muted">Angka sesuai cakupan masing-masing sumber. Data belum tersedia ditampilkan sebagai tanda pisah.</p></div><a class="button secondary" href="{{ route('reports.index') }}">Buka laporan</a></div>
    @include('overview.metrics')
    <div class="overview-columns">
        <section class="panel overview-panel" aria-labelledby="overview-coverage-title">
            <div class="overview-panel-heading"><h2 id="overview-coverage-title">Kelengkapan inventaris</h2><a href="{{ route('data-quality') }}">Detail kualitas</a></div>
            @if($snapshot['inventory'] === null)
                <p>Belum tersedia. Respons agregat tidak dapat dibaca atau diverifikasi.</p>
            @else
                <p><strong>{{ $snapshot['inventory']['complete'] ? 'Lengkap saat scan' : 'Cakupan masih parsial' }}</strong> · {{ number_format($snapshot['inventory']['pending_projection'], 0, ',', '.') }} menunggu proyeksi.</p>
                <dl class="overview-categories">@foreach(['equipment' => 'Equipment', 'component' => 'Component', 'part' => 'Part', 'system' => 'System', 'unknown' => 'Belum dikategorikan'] as $key => $label)<div><dt>{{ $label }}</dt><dd>{{ number_format($snapshot['inventory'][$key], 0, ',', '.') }}</dd></div>@endforeach</dl>
                <p class="muted">Kategori dari acuan Excel engineer dengan ID cocok tepat. Bukan status kondisi aset.</p>
            @endif
            <p class="overview-note">Kesegaran sumber belum dapat dipastikan. Scan terakhir dan waktu baca bukan jaminan data realtime.</p>
        </section>
        <section class="panel overview-panel" aria-labelledby="overview-work-title">
            <h2 id="overview-work-title">Lanjutkan pekerjaan</h2>
            <ul class="overview-links">
                <li><a href="{{ route('assets.index') }}">Master Asset & riwayat</a><span>Cari aset, WO, dan bukti yang tersedia.</span></li>
                <li><a href="{{ route('pdm.index') }}">Logbook inspeksi & PdM</a><span>Lihat pengukuran, permintaan, dan temuan lokal.</span></li>
                <li><a href="{{ route('action-board') }}">Action Board</a><span>WAPPR tetap terpisah dari gangguan tervalidasi.</span></li>
            </ul>
            <p class="overview-note">Entri PdM dan rekomendasi dapat saling terkait. Jumlahnya bukan total inspeksi unik. Skor kesehatan dan jumlah gangguan belum dinilai.</p>
        </section>
    </div>
    <p class="overview-footnote">Dibaca <time datetime="{{ $snapshot['observed_at'] }}">{{ $snapshot['observed_at'] }}</time> · Bukan waktu sinkronisasi sumber. Muat ulang halaman untuk membaca ulang.</p>
</x-shell>

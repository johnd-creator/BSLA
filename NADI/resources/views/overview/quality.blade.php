<x-shell title="Kualitas data">
    @include('overview.navigation')
    <div class="overview-heading"><div><h2>Dasar penggunaan data</h2><p class="muted">Ketersediaan, kelengkapan, dan kesegaran dipisahkan. Tidak ada skor kepercayaan buatan.</p></div><a class="button secondary" href="{{ route('reports.index') }}">Laporan</a></div>
    @include('overview.quality-table')
    <section class="panel overview-panel overview-scan" aria-labelledby="scan-title">
        <h2 id="scan-title">Bukti scan inventaris</h2>
        <dl class="overview-categories"><div><dt>Scan selesai terakhir</dt><dd>{{ $snapshot['inventory']['last_completed_at'] ?? 'Belum tersedia' }}</dd></div><div><dt>Menunggu proyeksi</dt><dd>{{ $snapshot['inventory'] === null ? '—' : number_format($snapshot['inventory']['pending_projection'], 0, ',', '.') }}</dd></div></dl>
        <p class="muted">Scan mencakup hierarki CS01 dalam BSR / IP. Aset tanpa kategori tetap dihitung; klasifikasi dokumen bukan perubahan data sumber atau keanggotaan Registry.</p>
    </section>
    <p class="overview-footnote">Dibaca {{ $snapshot['observed_at'] }} · Bukan waktu sinkronisasi sumber.</p>
</x-shell>

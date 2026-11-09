<x-shell title="Laporan">
    @include('overview.navigation')
    <div class="overview-heading"><div><h2>Laporan ringkasan saat ini</h2><p class="muted">Snapshot agregat dan batas kualitas data, bukan laporan tren atau periode historis.</p></div><a class="button primary" href="{{ route('reports.download') }}">Unduh CSV</a></div>
    @include('overview.metrics')
    <div class="panel table-scroll overview-quality"><table><caption class="sr-only">Sumber dan aturan hitung laporan</caption><thead><tr><th scope="col">Metrik</th><th scope="col">Sumber</th><th scope="col">Aturan hitung & batas</th></tr></thead><tbody>@foreach($snapshot['metrics'] as $metric)<tr><th scope="row">{{ $metric['label'] }}</th><td>{{ $metric['source'] }}</td><td>{{ $metric['definition'] }}</td></tr>@endforeach</tbody></table></div>
    <section class="panel overview-panel overview-scan"><h2>Isi unduhan</h2><p>CSV berisi jumlah, kategori inventaris, status cakupan, waktu scan jika tersedia, sumber, dan batas penggunaan. Nilai yang belum tersedia tetap kosong dengan status UNAVAILABLE, bukan nol.</p><p class="muted">Unduhan membaca ulang sumber saat diklik sehingga dapat berbeda dari tampilan ini. Tidak berisi identitas pengguna, isi temuan, atau payload mentah. Tidak dikirim ke pihak lain.</p></section>
    <p class="overview-footnote">Tampilan dibaca {{ $snapshot['observed_at'] }} · Waktu baca bukan waktu sinkronisasi. Angka hanya mewakili cakupan tertulis, tanpa klaim Asset Wellness.</p>
</x-shell>

<section class="panel ops-screen-placeholder" aria-labelledby="ops-placeholder-title" data-operations-placeholder>
    <div class="ops-placeholder-heading"><span class="ops-placeholder-code" aria-hidden="true">{{ $screen }}</span><div><p class="ops-kicker">LAYAR OPERASI / PLACEHOLDER</p><h2 id="ops-placeholder-title">{{ $screen }} · Referensi belum tersedia</h2><p>Kerangka navigasi siap. Diagram, equipment, jalur proses, dan parameter belum dibuat.</p></div></div>
    <dl class="ops-detail-states">
        <div><dt>Status operasi</dt><dd>? Unknown</dd><small>Belum ada sumber status.</small></div>
        <div><dt>Alarm DCS</dt><dd>Tidak terhubung</dd><small>Bukan pernyataan bebas alarm.</small></div>
        <div><dt>Asset Wellness</dt><dd>Belum dinilai</dd><small>Belum ada pemetaan Asset.</small></div>
    </dl>
    <div class="ops-placeholder-body"><h3>Yang diperlukan untuk melanjutkan layar ini</h3><ol><li>Gambar referensi {{ $screen }} dan susunan/jalur yang sudah diperiksa.</li><li>Pemetaan exact Asset untuk setiap simbol yang ingin dibuka.</li><li>Definisi parameter, tag, satuan, timestamp, dan kualitas sumber.</li></ol><p class="data-note">Tidak ada nilai contoh atau koneksi sumber yang diaktifkan dari halaman ini.</p><a class="button secondary small" href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL'])) }}">Lihat draft BOIL →</a></div>
</section>

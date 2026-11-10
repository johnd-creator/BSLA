@if($componentDetail)
    <section id="ops-component-detail" class="panel ops-detail" aria-labelledby="ops-detail-title" tabindex="-1">
        <div class="ops-detail-heading">
            <div><p class="ops-kicker">BOIL / {{ $componentDetail['group'] }} / DETAIL DRAFT</p><h2 id="ops-detail-title">{{ $componentDetail['label'] }}</h2><p>Label visual dari referensi · bukan identitas Asset terverifikasi.</p></div>
            <a class="button secondary small" href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL'])) }}#ops-overview-title">Tutup detail</a>
        </div>
        <dl class="ops-detail-states">
            <div><dt>Status operasi</dt><dd>? Unknown</dd><small>Belum ada sumber status.</small></div>
            <div><dt>Alarm DCS</dt><dd>Tidak terhubung</dd><small>Bukan pernyataan bebas alarm.</small></div>
            <div><dt>Asset Wellness</dt><dd>Belum dinilai</dd><small>Tidak mengikuti warna simulasi.</small></div>
        </dl>
        <div class="ops-detail-body">
            <section aria-labelledby="ops-readings-title">
                <h3 id="ops-readings-title">Pembacaan pada draft</h3>
                <p class="muted">Urutan dan satuan mengikuti simbol gambar. Nama parameter, satuan, dan tag masih perlu verifikasi.</p>
                <div class="ops-reading-grid">
                    @foreach($componentDetail['units'] as $readingUnit)
                        <div class="ops-reading"><span>Indikator {{ $loop->iteration }}</span><strong>— <small>{{ $readingUnit }}</small></strong><span>Kualitas: unknown</span><span>Waktu sumber: —</span></div>
                    @endforeach
                </div>
                <p class="data-note">Nilai kosong bukan nol. Tidak ada data live, histori, setpoint, atau perintah kontrol.</p>
            </section>
            <aside class="ops-mapping-note" aria-labelledby="ops-mapping-title">
                <h3 id="ops-mapping-title">Pemetaan belum tersedia</h3>
                <dl><div><dt>Canonical Asset</dt><dd>Belum dipetakan</dd></div><div><dt>Tag historian</dt><dd>Belum dipetakan</dd></div></dl>
                <p>Memilih aset pada Registry di bawah tidak menghubungkannya otomatis ke {{ $componentDetail['label'] }}.</p>
                <p>Perlu verifikasi exact Asset, arti parameter, satuan, timestamp, serta kualitas sebelum data diaktifkan.</p>
            </aside>
        </div>
    </section>
@else
    <p class="ops-detail-hint">Buka detail baca-saja lewat simbol diagram atau daftar komponen. Tidak ada perintah kontrol.</p>
@endif

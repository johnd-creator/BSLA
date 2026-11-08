<x-shell title="Historian · Pondasi" eyebrow="OPERASI · SIMULASI TERPISAH">
    <div class="section-intro"><p class="muted">Uji pola baca sesuai halaman tanpa mengakses DCS atau historian nyata.</p><span class="badge neutral">Read only · RAM</span></div>
    <div class="operations-boundary"><strong>SIMULASI · BUKAN DATA DCS</strong><p>Semua tag DEMO adalah data sintetis, tanpa mapping equipment atau KKS. Bukan HMI, alarm, kontrol, status running, maupun bukti operating exposure.</p></div>
    <section class="panel"><div class="operations-body">
        <form method="get" action="{{ route('operations.historian') }}" class="historian-picker">
            <div><label for="historian-page">Halaman demonstrasi</label><select id="historian-page" name="page">@foreach($pages as $key => $page)<option value="{{ $key }}" @selected($pageKey === $key)>{{ $page['title'] }}</option>@endforeach</select></div>
            <button class="button secondary" type="submit">Muat halaman</button>
        </form>
        <p class="data-note">Hanya {{ count($pages[$pageKey]['tags']) }} tag dalam daftar halaman ini yang diminta. Viewer berbagi cache di server. Sampel target 3–5 detik, bukan jaminan respons di bawah satu detik.</p>
    </div></section>
    @if(!$configured)
        <div class="notice info"><strong>Gateway simulasi belum diaktifkan</strong><p>Pondasi tersedia di kode. Tidak ada nilai atau polling historian aktif. Endpoint dan akses sumber nyata belum dikonfigurasi.</p></div>
    @else
        <section class="panel" data-historian data-page="{{ $pageKey }}" data-url="{{ route('operations.historian.action', 'subscribe') }}" data-csrf="{{ csrf_token() }}">
            <div class="panel-heading"><h2>Nilai halaman</h2><span class="badge neutral">SIMULASI</span></div>
            <div class="operations-body"><p role="status" data-historian-status>Belum ada sampel. Menunggu cache bersama.</p>
                <p class="historian-scroll-hint data-note">Geser tabel untuk melihat nilai, waktu sumber, dan kualitas.</p>
                <div class="table-wrap" tabindex="0" role="region" aria-label="Nilai historian simulasi, geser untuk kolom lainnya"><table class="data-table"><thead><tr><th>Tag demonstrasi</th><th>Nilai</th><th>Waktu sumber</th><th>Umur / kualitas</th></tr></thead><tbody data-historian-values></tbody></table></div>
                <p class="data-note" data-historian-context>Konteks umum per menit tidak aktif secara default. Data sinyal tidak berarti equipment sedang running.</p>
                <div class="historian-picker"><div><label for="history-tag">Riwayat sesuai permintaan</label><select id="history-tag" data-history-tag>@foreach($pages[$pageKey]['tags'] as $tag)<option>{{ $tag }}</option>@endforeach</select></div><button type="button" class="button secondary" data-history-load disabled>Lihat 15 menit · maks. 120 titik</button></div>
                <p class="data-note">Riwayat dibaca hanya saat tombol ditekan, tidak disimpan di database dan tidak menjamin cakupan kontinu.</p>
                <div data-history-result aria-live="polite"></div>
            </div>
        </section>
    @endif
    <div class="operations-readiness"><div><span>01 · Saat halaman dibuka</span><strong>Cache segera, atau no-data</strong><p>Tidak menunggu pembacaan sumber. Nilai kosong tetap kosong sampai sampel valid tiba.</p></div><div><span>02 · Saat halaman ditutup</span><strong>Lease + grace period</strong><p>Tag tanpa viewer berhenti setelah grace. Tab hilang dibersihkan lewat kedaluwarsa lease.</p></div><div><span>03 · Akses historian nyata</span><strong>Belum terhubung</strong><p>Menunggu adapter read-only, tag terverifikasi, satuan, kualitas dan izin akses. Tidak ada koneksi DCS yang dicoba.</p></div></div>
</x-shell>

<x-shell title="CEMS" eyebrow="OPERASI · READ ONLY">
    <section class="cems-page" data-cems data-refresh-url="{{ route('operations.cems.refresh') }}">
        <div class="operations-boundary"><strong>Pemantauan CEMS · jendela RAM 6 jam</strong><p>Pembacaan sumber setiap 5 detik oleh layanan bersama. Halaman ini hanya membaca cache, bukan HMI, alarm kepatuhan, atau kontrol PLC. Data cache hilang saat layanan restart dan kedaluwarsa setelah 6 jam; tidak disimpan oleh fitur ini. Data historis di sistem lain tidak diubah.</p></div>
        <p class="data-note" data-refresh-status role="status">Pembaruan tampilan setiap 5 detik saat halaman terlihat.</p>
        <div data-cems-content>@include('operations.cems-data')</div>
    </section>
</x-shell>

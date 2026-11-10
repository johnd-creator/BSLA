<x-shell title="Template rencana perlu ditinjau" eyebrow="PDM · IDENTITAS TETAP TERPISAH">
    <a class="back-link" href="{{ route('pdm.plans.show', $plan) }}">← Rencana inspeksi</a>
    <section class="panel detail-panel">
        <h2>Template rencana tidak sama dengan katalog saat ini</h2>
        <p>{{ $plan->reference() }} · {{ $plan->title }}</p>
        <p>Template mungkin berubah, dihapus dari katalog, atau masih perlu review. Form baru tidak diisi dari konteks yang berbeda. Rencana dan pengukuran lama tetap tersimpan.</p>
        <p class="data-note">Tinjau identitas titik, satuan dan konteks. Buat rencana terpisah untuk template baru bila diperlukan; jangan menggabungkan cakupan otomatis.</p>
        <a class="button secondary" href="{{ route('pdm.plans.show', $plan) }}">Kembali ke rencana</a>
        <a class="button secondary" href="{{ route('pdm.templates', ['asset_ref' => $plan->asset_ref]) }}">Tinjau katalog saat ini</a>
    </section>
</x-shell>

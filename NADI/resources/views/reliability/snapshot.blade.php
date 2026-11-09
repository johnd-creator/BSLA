<x-shell :title="'Snapshot reliability #'.$snapshot->id" eyebrow="HASIL TERSIMPAN · TIDAK DITIMPA">
<a class="back-link" href="{{ route('reliability.index', ['asset_ref'=>$snapshot->asset_ref, 'year'=>$snapshot->year]) }}">← Bukti terbaru</a>
<div class="notice {{ $changed ? 'error' : '' }}">{{ $changed ? 'Bukti atau ketersediaan sumber berubah sejak snapshot. Hasil ini historis; buka bukti terbaru sebelum memakai.' : 'Basis bukti saat ini sama dengan snapshot pada pemeriksaan ini. Ini bukan bukti kesegaran sumber.' }}</div>
<a class="button secondary" href="{{ route('reliability.snapshots.download', $snapshot) }}">Unduh snapshot JSON</a>
@include('reliability.approval')
@include('reliability.report')
</x-shell>

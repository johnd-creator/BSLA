@if($inspection && $inspection->pdmReviewState())
    <div class="notice info" role="status"><strong>Analisis perlu ditinjau.</strong>
        @if($inspection->pdmReviewState() === 'stale') Nilai atau konteks pengukuran berubah setelah analisis terakhir ditinjau. @else Versi pengukuran yang mendasari analisis lama belum tercatat. @endif
        Temuan, rekomendasi dan status tindak lanjut tetap disimpan; kesesuaiannya dengan pengukuran terkini belum dikonfirmasi.
        <a class="text-link" href="{{ route('pdm.show', $inspection->pdm_activity_id) }}">Lihat pengukuran terkini →</a>
        @can('update-inspection-draft', $inspection)<a class="text-link" href="{{ route('inspections.edit', $inspection) }}">Tinjau analisis →</a>@endcan
    </div>
@endif

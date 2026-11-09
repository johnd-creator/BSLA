<section class="panel detail-panel"><h2>Riwayat aktivitas tercatat</h2><p class="data-note">Jejak perubahan mulai fitur feed aktif. Tidak merekonstruksi perubahan lama; isi draft di atas adalah versi terkini. Koreksi baru PdM menyimpan nilai sebelum dan sesudah. Jejak lama tanpa rincian tidak menyatakan nilainya tidak pernah berubah.</p>
    @foreach($activityHistory as $entry)<details class="workspace-audit" id="activity-{{ $entry->id }}" @if(request('activity_id') == $entry->id) open @endif><summary>{{ $entry->action === 'created' ? 'Dibuat' : 'Diperbarui' }} · v{{ $entry->version }} · {{ $entry->actor?->name ?? 'Pelaku tidak tersedia' }} · Waktu simpan {{ $entry->created_at->format('d M Y H:i:s') }} UTC</summary>
        <p>Aset saat pencatatan: {{ $entry->asset_ref ?? 'Belum ditautkan' }}</p>
        @foreach($entry->changes as $field=>$change)
            <div><h3>{{ ['finding'=>'Temuan', 'recommendation'=>'Rekomendasi', 'follow_up_status'=>'Status tindak lanjut', 'target_completion'=>'Target selesai', 'readings'=>'Hasil pengukuran', 'instrument'=>'Alat / laporan', 'measurement_mode'=>'Mode / basis', 'operating_condition'=>'Kondisi operasi', 'asset_selection_note'=>'Dasar pemilihan aset / sampling', 'notes'=>'Catatan', 'title'=>'Judul', 'pdm_basis'=>'Pengukuran yang ditinjau untuk analisis'][$field] ?? $field }}</h3>
            @if($field === 'pdm_basis')
                <p>Sebelum: {{ isset($change['before']['version']) ? 'Versi '.$change['before']['version'] : 'Belum tercatat' }}</p>
                <p>Sesudah: versi {{ $change['after']['version'] }} · nilai dan konteks pada saat tinjauan dicatat</p>
            @elseif($field === 'readings')
                @php($oldReadings = json_decode($change['before'] ?? '{}', true) ?? [])
                @php($newReadings = json_decode($change['after'] ?? '{}', true) ?? [])
                @foreach(array_unique([...array_keys($oldReadings), ...array_keys($newReadings)]) as $key)
                    @if(($oldReadings[$key] ?? null) !== ($newReadings[$key] ?? null))
                        @php($point = collect($activity->template_snapshot['fields'] ?? [])->firstWhere('key', $key))
                        <p class="draft-long-text"><strong>{{ $point['label'] ?? $key }}</strong><br>
                        Sebelum: {{ $oldReadings[$key]['value'] ?? 'Belum diukur' }} {{ $oldReadings[$key]['unit'] ?? '' }}<br>
                        Sesudah: {{ $newReadings[$key]['value'] ?? 'Belum diukur' }} {{ $newReadings[$key]['unit'] ?? '' }}</p>
                    @endif
                @endforeach
            @else
                <p class="draft-long-text">Sebelum: {{ $change['before'] ?? 'Belum dicatat' }}</p><p class="draft-long-text">Sesudah: {{ $change['after'] ?? 'Belum dicatat' }}</p>
            @endif
            </div>
        @endforeach
    </details>@endforeach
    @if($activityHistory->isEmpty())<p class="data-note">Belum ada jejak perubahan pada pilihan ini. Tidak menyatakan draft belum pernah berubah.</p>@endif
    <div class="pagination">{{ $activityHistory->links() }}</div>
    @if(request('activity_id'))<a href="{{ request()->url() }}">Lihat riwayat terbaru</a>@endif
</section>

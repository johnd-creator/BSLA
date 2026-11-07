<section class="panel detail-panel"><h2>Riwayat aktivitas tercatat</h2><p class="data-note">Jejak perubahan mulai fitur feed aktif. Tidak merekonstruksi perubahan lama; isi draft di atas adalah versi terkini. Pengukuran PdM hanya mencatat tindakan dan versi, bukan salinan nilai sebelumnya.</p>
    @foreach($activityHistory as $entry)<details class="workspace-audit" id="activity-{{ $entry->id }}" @if(request('activity_id') == $entry->id) open @endif><summary>{{ $entry->action === 'created' ? 'Dibuat' : 'Diperbarui' }} · v{{ $entry->version }} · {{ $entry->actor?->name ?? 'Pelaku tidak tersedia' }} · Waktu simpan {{ $entry->created_at->format('d M Y H:i:s') }} UTC</summary>
        <p>Aset saat pencatatan: {{ $entry->asset_ref ?? 'Belum ditautkan' }}</p>
        @foreach($entry->changes as $field=>$change)<div><h3>{{ ['recommendation'=>'Rekomendasi', 'follow_up_status'=>'Status tindak lanjut', 'target_completion'=>'Target selesai'][$field] ?? $field }}</h3><p class="draft-long-text">Sebelum: {{ $change['before'] ?? 'Belum dicatat' }}</p><p class="draft-long-text">Sesudah: {{ $change['after'] ?? 'Belum dicatat' }}</p></div>@endforeach
    </details>@endforeach
    @if($activityHistory->isEmpty())<p class="data-note">Belum ada jejak perubahan pada pilihan ini. Tidak menyatakan draft belum pernah berubah.</p>@endif
    <div class="pagination">{{ $activityHistory->links() }}</div>
    @if(request('activity_id'))<a href="{{ request()->url() }}">Lihat riwayat terbaru</a>@endif
</section>

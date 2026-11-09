<x-shell title="Bukti efektivitas" eyebrow="TINDAK LANJUT · KEPUTUSAN ENGINEER">
    <a class="back-link" href="{{ route('action-board') }}#follow-ups-title">← Action Board</a>
    <section class="panel detail-panel">
        <div class="panel-heading"><div><h2>{{ $inspection->reference() }}</h2><p class="draft-long-text">{{ $inspection->recommendation }}</p></div><a class="text-link" href="{{ route('inspections.show', $inspection) }}">Detail rekomendasi →</a></div>
        <dl class="detail-grid"><div><dt>Aset persis</dt><dd>{{ $inspection->asset_ref ?: 'Belum tertaut' }}</dd></div><div><dt>Pelaksanaan</dt><dd>{{ \App\Models\InspectionDraft::FOLLOW_UP_STATUSES[$inspection->follow_up_status] }}</dd></div><div><dt>Efektivitas</dt><dd>{{ $evidence->label($evidence->state($latest, $inspection)) }}</dd></div></dl>
        <p class="data-note">Selesai bukan bukti efektif. Nilai sebelum dan sesudah adalah pengukuran lokal, bukan bukti sebab-akibat atau persetujuan pekerjaan. Penilaian tetap dilakukan engineer penyusun.</p>
    </section>
    @include('pdm.review-notice')
    @can('update-inspection-draft', $inspection)
    <section class="panel detail-panel">
        <h2>1. Pilih bukti pengukuran</h2>
        <p class="field-hint">Pilih dua pengukuran pada aset ini. Daftar memuat 50 aktivitas terbaru dan bukti terpilih. Pilihan ini belum menyimpan review.</p>
        <form method="get" class="filters" action="{{ route('inspections.effectiveness', $inspection) }}">
            @foreach(['before'=>'Pengukuran sebelum', 'after'=>'Pengukuran sesudah'] as $key=>$label)
            <div><label for="{{ $key }}_id">{{ $label }}</label><select id="{{ $key }}_id" name="{{ $key }}_id"><option value="">Belum dipilih</option>
                @foreach($candidates->concat(collect([$before, $after])->filter())->unique('id') as $candidate)
                <option value="{{ $candidate->id }}" @selected(($key==='before' ? $before?->id : $after?->id)===$candidate->id)>{{ $candidate->reference() }} · {{ $candidate->measurementDate() }} · {{ $candidate->template_id }}</option>
                @endforeach
            </select></div>
            @endforeach
            <button class="button secondary">Tampilkan bukti</button>
        </form>
        <details><summary>Pilih catatan lama dengan ID</summary><p class="field-hint">Gunakan ID numerik dari referensi PDM-DRAFT pada Logbook PdM. Aset tetap diperiksa oleh server.</p><form method="get" class="filters" action="{{ route('inspections.effectiveness', $inspection) }}"><div><label for="older_before">ID sebelum</label><input id="older_before" name="before_id" type="number" min="1" value="{{ $before?->id }}"></div><div><label for="older_after">ID sesudah</label><input id="older_after" name="after_id" type="number" min="1" value="{{ $after?->id }}"></div><button class="button secondary">Tampilkan catatan</button></form></details>
        <details><summary>Rujukan pengukuran aset ini (maksimal 50 terbaru)</summary>
            <div class="table-scroll" role="region" tabindex="0" aria-label="Rujukan pengukuran"><table><thead><tr><th>ID</th><th>Pengukuran</th><th>Tanggal / ketelitian</th><th>Template</th></tr></thead><tbody>
            @forelse($candidates as $candidate)<tr><td>{{ $candidate->id }}</td><td><a class="text-link" href="{{ route('pdm.show', $candidate) }}">{{ $candidate->reference() }}</a><small>{{ $candidate->title }}</small></td><td>{{ $candidate->measurementLabel() }}<small>{{ $candidate->precisionLabel() }}</small></td><td>{{ $candidate->template_id }}</td></tr>@empty<tr><td colspan="4">Belum ada pengukuran pada aset ini. Jangan mengisi angka pengganti.</td></tr>@endforelse
            </tbody></table></div>
        </details>
    </section>
    <section class="panel detail-panel">
        <h2>2. Catat tindakan dan keputusan</h2>
        @if($errors->any())<div role="alert" class="data-note"><strong>Review belum tersimpan.</strong><ul>@foreach($errors->all() as $error)<li>{{ $error }}</li>@endforeach</ul></div>@endif
        <div class="inspection-result-grid">
        @foreach(['Sebelum' => $before, 'Sesudah' => $after] as $label => $measurement)
            <section><h3>{{ $label }}</h3>@if($measurement)<p><a class="text-link" href="{{ route('pdm.show', $measurement) }}">{{ $measurement->reference() }}</a> · versi {{ $measurement->version }}<br>{{ $measurement->measurementLabel() }} · {{ $measurement->precisionLabel() }}</p><dl>@foreach(\App\Services\PdmTrend::CONTEXT as $context)<dt>{{ ['measurement_mode'=>'Mode','instrument'=>'Alat / laporan','operating_condition'=>'Kondisi operasi','asset_selection_note'=>'Titik / lokasi'][$context] }}</dt><dd>{{ $measurement->$context ?: 'Belum dicatat' }}</dd>@endforeach</dl>@else<p>Belum dipilih.</p>@endif</section>
        @endforeach
        </div>
        @if($before || $after)
        <p class="data-note">Nilai berjajar belum membuktikan kesebandingan. Template, satuan, konteks dan urutan tanggal diperiksa kembali saat review disimpan.</p>
        <div class="table-scroll" role="region" tabindex="0" aria-label="Nilai pengukuran sebelum dan sesudah"><table><thead><tr><th>Titik pada template sebelum</th><th>Sebelum</th><th>Sesudah</th></tr></thead><tbody>
        @foreach(($before?->template_snapshot['fields'] ?? []) as $field)
            @if(($field['type'] ?? null)==='number')<tr><td>{{ $field['label'] }}<small>{{ $field['key'] }}</small></td><td>{{ $before->readings[$field['key']]['value'] ?? 'Belum diukur' }} {{ $before->readings[$field['key']]['unit'] ?? '' }}</td><td>{{ $after?->readings[$field['key']]['value'] ?? 'Belum diukur' }} {{ $after?->readings[$field['key']]['unit'] ?? '' }}</td></tr>@endif
        @endforeach
        </tbody></table></div>
        @endif
        <form method="post" action="{{ route('inspections.effectiveness.store', $inspection) }}" class="draft-form stack">
            @csrf
            <input type="hidden" name="request_key" value="{{ old('request_key', (string) \Illuminate\Support\Str::uuid()) }}">
            <input type="hidden" name="inspection_version" value="{{ $inspection->version }}">
            <input type="hidden" name="latest_review_id" value="{{ $latest?->id ?? 0 }}">
            @foreach(['before' => $before, 'after' => $after] as $key => $measurement)
                <input type="hidden" name="{{ $key }}_id" value="{{ $measurement?->id }}"><input type="hidden" name="{{ $key }}_version" value="{{ $measurement?->version }}">
            @endforeach
            <div><label for="action_taken">Tindakan yang benar-benar dilaksanakan</label><textarea id="action_taken" name="action_taken" maxlength="4000" required rows="3">{{ old('action_taken', $latest?->action_taken) }}</textarea></div>
            <div><label for="completed_on">Tanggal tindakan selesai</label><input id="completed_on" name="completed_on" type="date" max="{{ now('Asia/Jakarta')->toDateString() }}" value="{{ old('completed_on', $latest?->completed_on) }}" required><p class="field-hint">Tanggal saja, tanpa jam rekaan. Untuk keputusan efektif/perlu tindakan lagi, bukti sebelum harus lebih awal dan sesudah lebih akhir dari tanggal ini.</p></div>
            <div><label for="point">Titik yang dinilai</label><select id="point" name="point"><option value="">Belum dipilih</option>@foreach(($before?->template_snapshot['fields'] ?? []) as $field)@if(($field['type'] ?? null)==='number')<option value="{{ $field['key'] }}" @selected(old('point', $latest?->point)===$field['key'])>{{ $field['label'] }} · {{ $field['unit'] ?? 'Satuan belum tersedia' }}</option>@endif @endforeach</select></div>
            <div><label for="decision">Keputusan engineer</label><select id="decision" name="decision" required>@foreach(\App\Models\ActionEffectivenessReview::DECISIONS as $value=>$label)<option value="{{ $value }}" @selected(old('decision', 'inconclusive')===$value)>{{ $label }}</option>@endforeach</select></div>
            <div><label for="reason">Alasan, kriteria efektivitas dan tindak lanjut berikutnya</label><textarea id="reason" name="reason" maxlength="4000" required rows="4">{{ old('reason') }}</textarea><p class="field-hint">Jelaskan kriteria dan konteks yang ditinjau. Nilai turun tidak otomatis berarti membaik. Jika bukti belum cukup atau tidak sebanding, pilih Belum dapat dinilai.</p></div>
            <label><input type="checkbox" name="acknowledge_review" value="1" required @checked(old('acknowledge_review'))> Saya meninjau tindakan, tanggal, nilai, satuan, titik dan konteks ini. Ini penilaian lokal saya, bukan approval atau diagnosis otomatis.</label>
            <div class="form-actions"><button class="button primary">Simpan review baru</button><a class="button secondary" href="{{ route('action-board') }}#follow-ups-title">Batal</a></div>
        </form>
    </section>
    @endcan
    <section class="panel detail-panel"><h2>Riwayat keputusan dan bukti saat ditinjau</h2>
        @forelse($history as $review)
        <article><h3>Review {{ $review->revision }} · {{ \App\Models\ActionEffectivenessReview::DECISIONS[$review->decision] }}</h3><p>{{ $review->author->name }} · {{ $review->created_at->timezone('Asia/Jakarta')->format('d M Y H:i') }} WIB</p><p class="draft-long-text">{{ $review->action_taken }}</p><p>Tanggal tindakan: {{ $review->completed_on }}</p><p class="draft-long-text">{{ $review->reason }}</p>
            <details><summary>Bukti tersimpan pada review {{ $review->revision }}</summary><p class="data-note">Snapshot saat penilaian; koreksi pengukuran berikutnya tidak menulis ulang bukti ini.</p><p>Rekomendasi saat ditinjau: {{ $review->evidence['inspection']['record']['recommendation'] ?? 'Belum tercatat' }}</p>
                @foreach(['before'=>'Sebelum','after'=>'Sesudah'] as $key=>$label)
                    @php($saved = $review->evidence[$key] ?? null)
                    <p><strong>{{ $label }}:</strong> @if($saved)<a class="text-link" href="{{ route('pdm.show', $saved['id']) }}">{{ $saved['reference'] }}</a> · versi {{ $saved['basis']['version'] }} · {{ $saved['measurement_label'] }} · {{ $saved['precision_label'] }}<br>Nilai titik {{ $review->point ?: 'belum dipilih' }}: {{ $saved['readings'][$review->point]['value'] ?? 'Belum diukur' }} {{ $saved['readings'][$review->point]['unit'] ?? '' }}<br>Konteks: {{ implode(' · ', $saved['context']) }}@else Belum dipilih @endif</p>
                @endforeach
                @if(!($review->evidence['comparison']['valid'] ?? false))<p class="data-note">{{ $review->evidence['comparison']['blocker'] ?? 'Bukti belum cukup.' }}</p>@endif
            </details>
        </article>
        @empty<p>Belum ada penilaian efektivitas. Status Selesai, nilai kosong atau tidak adanya pengukuran tidak dianggap efektif.</p>@endforelse
        <div class="pagination">{{ $history->links() }}</div>
        <p class="data-note">Koreksi dicatat sebagai review baru. Tidak ada penghapusan sejarah, perubahan WO, penilaian risiko, atau perubahan status tindak lanjut otomatis.</p>
    </section>
</x-shell>

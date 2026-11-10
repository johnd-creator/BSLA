<x-shell title="Pengaturan Asset Wellness" eyebrow="DRAFT · BELUM DIVALIDASI ENGINEER">
    <section class="panel wellness-intro"><span class="draft-label">Usulan metode, bukan pengesahan</span><h2>Catat aturan sebelum menilai kondisi</h2><p>{{ $assetRef }} · Periode bukti {{ $period->label() }}</p><p>Criticality, rentang PdM, usia data dan daftar bukti dicatat tanpa nilai bawaan. Semua hasil Wellness tetap kosong sampai metode dan bukti divalidasi. Approval KPI Reliability tidak berlaku untuk Wellness.</p><a class="text-link" href="{{ route('wellness.index', ['asset_ref'=>$assetRef, ...$period->query()]) }}">← Kembali ke bukti Wellness</a></section>
    @include('wellness.policy-summary')
    @can('write-wellness-policies')
        @if($report['storage_ready'] && (!$latest || $latest->created_by === auth()->id()))
            @php($draft = $latest?->rules ?? [])
            <form method="post" action="{{ route('wellness.policy.store') }}" class="panel wellness-policy-form">
                @csrf
                <input type="hidden" name="asset_ref" value="{{ $assetRef }}">@foreach($period->query() as $name=>$value)<input type="hidden" name="{{ $name }}" value="{{ $value }}">@endforeach
                <input type="hidden" name="request_key" value="{{ old('request_key', $requestKey) }}">
                <input type="hidden" name="previous_revision" value="{{ old('previous_revision', $latest?->revision ?? 0) }}">
                <h2>{{ $latest ? 'Buat revisi usulan' : 'Usulan awal' }}</h2><p class="data-note">Kosong berarti belum diputuskan. Revisi lama dipertahankan. Hanya engineer pencatat yang dapat merevisi pengaturan ini.</p>
                <fieldset><legend>Criticality aset</legend><p>Konsekuensi jika aset gagal, terpisah dari kondisi dan urgensi. Tidak ada kategori atau bobot yang ditetapkan otomatis.</p>
                    <label>Label usulan criticality <input name="criticality_label" maxlength="80" value="{{ old('criticality_label', $draft['criticality_label'] ?? '') }}" placeholder="Belum dipetakan"></label>
                    <label>Dasar konsekuensi dan referensi <textarea name="criticality_basis" rows="3" maxlength="2000">{{ old('criticality_basis', $draft['criticality_basis'] ?? '') }}</textarea></label>
                </fieldset>
                <fieldset><legend>Usia dan bukti wajib tiap komponen</legend><p>Usia dalam hari kalender dibanding {{ $period->annual ? 'tanggal baca WIB' : 'tanggal akhir periode WIB, menggunakan revisi bukti terkini' }}, bukan jam presisi. Ini bukan rekonstruksi pengetahuan yang tersedia pada masa lalu. Usia untuk log operasi/failure/WO masih usulan: basis waktu sumber perlu disepakati. Daftar bukti diperiksa manual, bukan dihitung dari jumlah record.</p>
                    <div class="wellness-policy-grid">@foreach(\App\Services\AssetWellness::COMPONENTS as $key => $component)<div>
                        <h3>{{ $component['label'] }}</h3><label>Usulan bobot (%)<input type="number" step="0.01" min="0" max="100" name="components[{{ $key }}][weight]" value="{{ old('components.'.$key.'.weight', $draft['components'][$key]['weight'] ?? '') }}" placeholder="Belum diputuskan"></label><label>Usulan cara normalisasi dan pengecualian<textarea name="components[{{ $key }}][normalization]" maxlength="2000" rows="3">{{ old('components.'.$key.'.normalization', $draft['components'][$key]['normalization'] ?? '') }}</textarea></label><p class="data-note">Bobot dan teks metode masih draft. Total 100 bukan validasi dan tidak mengaktifkan skor.</p><label>Usulan usia maksimum (hari)<input type="number" name="components[{{ $key }}][max_age_days]" min="0" max="36500" value="{{ old('components.'.$key.'.max_age_days', $draft['components'][$key]['max_age_days'] ?? '') }}" placeholder="Belum diputuskan"></label>
                        <label>Bukti wajib dan cara memeriksa kelengkapannya<textarea name="components[{{ $key }}][required_evidence]" rows="3" maxlength="2000">{{ old('components.'.$key.'.required_evidence', $draft['components'][$key]['required_evidence'] ?? '') }}</textarea></label>
                    </div>@endforeach</div>
                </fieldset>
                <fieldset><legend>Usulan batas PdM per titik dan konteks exact</legend><p>Batas inklusif, minimal satu sisi. Ini tidak mengaktifkan alarm, normalisasi atau skor. Satuan, template, metode, alat, mode, kondisi operasi dan dasar pemilihan aset dikunci dari pengukuran acuan. Jangan menggabungkan konteks berbeda.</p>
                    @if($anchors->isEmpty())<p class="alert warning">Belum ada pengukuran acuan untuk aset/periode ini. Criticality dan kebutuhan bukti tetap dapat disimpan. Catat pengukuran dengan titik, satuan dan konteks terlebih dahulu untuk mengusulkan batas PdM.</p>
                    @else
                        <details><summary>Lihat kode titik dan konteks pengukuran acuan</summary><p class="data-note">100 pengukuran terbaru pada periode ini, ditambah acuan revisi tersimpan. Buka sumber untuk riwayat penuh.</p>
                            @foreach($anchors as $anchor)<div class="wellness-anchor"><strong><a class="text-link" href="{{ route('pdm.show', $anchor) }}">{{ $anchor->reference() }}</a> · {{ $anchor->measurementLabel() }}</strong><p>{{ $anchor->method }} · {{ $anchor->measurement_mode }} · {{ $anchor->instrument }} · {{ $anchor->operating_condition }}</p><ul>@foreach($anchor->template_snapshot['fields'] ?? [] as $field)@if(($field['type'] ?? null) === 'number')<li>{{ $field['key'] }}: {{ $field['label'] }} · {{ $anchor->readings[$field['key']]['unit'] ?? $field['unit'] ?? 'Satuan belum diketahui' }}</li>@endif @endforeach</ul></div>@endforeach
                        </details>
                        @foreach($anchors as $anchor)<input type="hidden" name="anchor_fingerprints[{{ $anchor->id }}]" value="{{ $anchor->analysisBasis()['fingerprint'] }}">@endforeach
                        @php($pointRows = old('pdm_rules', [...($draft['pdm_rules'] ?? []), ...((count($draft['pdm_rules'] ?? []) < 10) ? [[]] : [])]))
                        @foreach($pointRows as $i => $point)
                            <div class="wellness-rule"><h3>Usulan titik {{ $i + 1 }}</h3><div class="wellness-policy-grid">
                                <label>Pengukuran acuan<select name="pdm_rules[{{ $i }}][anchor_id]"><option value="">Pilih acuan</option>@foreach($anchors as $anchor)<option value="{{ $anchor->id }}" @selected((string)($point['anchor_id'] ?? '') === (string)$anchor->id)>{{ $anchor->reference() }} · {{ $anchor->measurementLabel() }} · {{ $anchor->method }}</option>@endforeach</select></label>
                                <label>Kode titik (lihat daftar acuan)<input name="pdm_rules[{{ $i }}][point]" maxlength="100" value="{{ $point['point'] ?? '' }}"></label>
                                <label>Batas bawah inklusif<input type="number" step="any" name="pdm_rules[{{ $i }}][lower]" value="{{ $point['lower'] ?? '' }}" placeholder="Belum diusulkan"></label>
                                <label>Batas atas inklusif<input type="number" step="any" name="pdm_rules[{{ $i }}][upper]" value="{{ $point['upper'] ?? '' }}" placeholder="Belum diusulkan"></label>
                                <label>Usulan usia maksimum titik (hari)<input type="number" min="0" max="36500" name="pdm_rules[{{ $i }}][max_age_days]" value="{{ $point['max_age_days'] ?? '' }}" placeholder="Belum diputuskan"></label>
                                <label>Dasar batas, referensi dan bukti kualitas alat<textarea name="pdm_rules[{{ $i }}][requirement]" rows="2" maxlength="2000">{{ $point['requirement'] ?? '' }}</textarea></label>
                            </div><label class="wellness-check"><input type="checkbox" name="pdm_rules[{{ $i }}][remove]" value="1" @checked($point['remove'] ?? false)> Hapus usulan titik ini pada revisi baru (riwayat tetap ada)</label></div>
                        @endforeach
                        <p class="data-note">Simpan untuk menambahkan baris berikutnya, maksimal 10 usulan titik per revisi. Baris kosong diabaikan. Usia per titik berdiri sendiri; tidak diam-diam mewarisi batas komponen.</p>
                    @endif
                </fieldset>
                <label>Referensi usulan keseluruhan<textarea name="evidence" rows="3" minlength="5" maxlength="4000" required>{{ old('evidence', $latest?->evidence) }}</textarea></label>
                <label>Alasan revisi<textarea name="reason" rows="2" minlength="5" maxlength="2000" required>{{ old('reason') }}</textarea></label>
                <label class="wellness-check"><input type="checkbox" name="acknowledge_draft" value="1" @checked(old('acknowledge_draft')) required> Saya memahami ini usulan draft, bukan validasi engineer, pengesahan metode atau keputusan operasi.</label>
                <div class="form-actions"><button class="button primary" type="submit">Simpan revisi draft</button><a class="button secondary" href="{{ route('wellness.index', ['asset_ref'=>$assetRef, ...$period->query()]) }}">Batal</a></div>
            </form>
        @elseif($latest)<p class="alert warning">Pengaturan ini dicatat engineer lain. Anda dapat membaca riwayat, tetapi tidak mengubah catatan miliknya.</p>@endif
    @else<p class="data-note">Peran Anda dapat membaca. Pengaturan draft hanya dapat ditulis engineer.</p>@endcan
    @if($policies)<section class="panel wellness-method"><h2>Riwayat revisi draft</h2>@forelse($policies as $policy)<details><summary>Revisi {{ $policy->revision }} · {{ $policy->author?->name ?? 'Pencatat' }} · {{ $policy->created_at->format('d M Y H:i') }} UTC</summary><p><strong>Alasan:</strong> {{ $policy->reason }}</p><p><strong>Referensi:</strong> {{ $policy->evidence }}</p><p>Criticality usulan: {{ $policy->rules['criticality_label'] ?? 'Belum dipetakan' }}. {{ $policy->rules['criticality_basis'] ?? '' }}</p>
        @foreach(\App\Services\AssetWellness::COMPONENTS as $key => $component)<p><strong>{{ $component['label'] }}:</strong> usia usulan {{ $policy->rules['components'][$key]['max_age_days'] ?? 'Belum diputuskan' }} hari · {{ $policy->rules['components'][$key]['required_evidence'] ?? 'Bukti wajib belum ditentukan' }}</p>@endforeach
        @foreach($policy->rules['pdm_rules'] ?? [] as $point)<p>{{ $point['scope']['template_id'] }} · {{ $point['point'] }} · {{ $point['unit'] }} · Batas {{ $point['lower'] ?? 'Terbuka' }} sampai {{ $point['upper'] ?? 'Terbuka' }} · Usia {{ $point['max_age_days'] ?? 'Belum diputuskan' }} hari. {{ $point['requirement'] }}</p>@endforeach
        <p class="data-note">{{ $policy->rules['schema_version'] }} · DRAFT_NOT_APPROVED · tidak ada skor atau approval.</p></details>@empty<p>Belum ada pengaturan tersimpan.</p>@endforelse {{ $policies->links() }}</section>@endif
</x-shell>

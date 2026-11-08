@php
    use App\Models\AssetDisruptionWorkOrder;
    $activeLinks = $event->workOrders->where('relation_state', '!=', 'removed');
    $oldRef = old('work_order_ref');
@endphp
<x-shell title="Hubungkan WO dengan gangguan" eyebrow="KORELASI ENGINEER · BUKAN VALIDASI FAILURE">
    <a class="back-link" href="{{ route('disruptions.show', $event) }}">← {{ $event->reference() }}</a>
    <section class="panel detail-panel disruption-detail">
        <h2>{{ $event->reference() }} · {{ $event->asset_ref }}</h2>
        <p>Pilih WO milik aset utama ini. Satu kejadian boleh memiliki beberapa WO. Kecocokan identitas aset tidak membuktikan WO tersebut menyebabkan atau memperbaiki gangguan.</p>
        <p class="data-note">{{ $event->status === 'voided' ? 'Catatan gangguan dibatalkan; hubungan tetap hanya bagian dari riwayat.' : 'Hubungan baru selalu belum dipastikan. Tidak mengubah tipe, waktu, dampak, atau status gangguan.' }} Status WAPPR tetap backlog; CLOSE bukan bukti failure, downtime, MTBF, atau MTTR.</p>
        <x-field-error name="version" />
        @if($errors->has('version'))<a class="text-link" href="{{ route('disruptions.work-orders', $event) }}">Buka ulang versi terbaru</a>@endif
    </section>
    <section class="panel detail-panel disruption-detail stack">
        <h2>Pilih WO dari aset ini</h2>
        <form method="get" action="{{ route('disruptions.work-orders', $event) }}" class="form-grid">
            <div><label for="wo_number">Cari nomor WO persis (opsional)</label><input id="wo_number" name="wo_number" maxlength="100" value="{{ request('wo_number') }}" placeholder="Contoh: BSR26/19873"><x-field-error name="wo_number" /></div>
            <div class="form-actions"><button class="button secondary" type="submit">Cari WO</button><a class="text-link" href="{{ route('disruptions.work-orders', $event) }}">Tampilkan daftar</a></div>
        </form>
        @if($page === null)<div class="notice error">Daftar WO belum dapat diverifikasi. Bukan berarti tidak ada WO. Hubungan yang sudah dicatat tetap terlihat di bawah.</div>
        @elseif(count($page['items']) === 0)<p>Tidak ada WO pada filter ini. Referensi manual tidak otomatis dijadikan hubungan.</p>
        @else<p class="field-hint">{{ count($page['items']) }} dari {{ $page['meta']['total'] }} WO dalam cakupan API. Pilih satu, simpan, lalu ulangi untuk WO tambahan. Perpindahan halaman tidak menyimpan isian.</p>@endif
        <form method="post" action="{{ route('disruptions.work-orders.store', $event) }}" class="stack">
            @csrf
            <input type="hidden" name="version" value="{{ old('version', $event->version) }}">
            <div><label for="work_order_ref">WO untuk ditautkan</label><select id="work_order_ref" name="work_order_ref" required aria-describedby="wo-link-hint" @error('work_order_ref') aria-invalid="true" @enderror>
                <option value="">Pilih WO</option>
                @if($oldRef && ! collect($page['items'] ?? [])->contains('work_order_id', $oldRef))<option value="{{ $oldRef }}" selected>{{ $oldRef }} · pilihan sebelumnya, perlu verifikasi ulang</option>@endif
                @foreach($page['items'] ?? [] as $record)<option value="{{ $record['work_order_id'] }}" @selected($oldRef === $record['work_order_id']) @disabled($activeLinks->contains('work_order_ref', $record['work_order_id']))>{{ $record['work_order_number'] ?: $record['work_order_id'] }} · {{ $record['status'] ?: 'Status belum diketahui' }} · {{ $record['description'] ?: 'Deskripsi belum tersedia' }}{{ $activeLinks->contains('work_order_ref', $record['work_order_id']) ? ' · sudah tertaut' : '' }}</option>@endforeach
            </select><x-field-error name="work_order_ref" /><p id="wo-link-hint" class="field-hint">Identitas WO dan aset diperiksa lagi saat simpan melalui Mart. Maksimal 20 hubungan aktif; tidak ada koleksi atau perubahan ke Maximo.</p></div>
            <div><label for="note">Catatan awal hubungan (opsional)</label><textarea id="note" name="note" rows="2" maxlength="2000">{{ old('note') }}</textarea><x-field-error name="note" /></div>
            <div class="form-actions"><a class="button secondary" href="{{ route('disruptions.show', $event) }}">Kembali tanpa menambah</a><button class="button primary" type="submit" @disabled($page === null)>Tautkan sebagai belum dipastikan</button></div>
        </form>
        @if($page && ($page['meta']['offset'] > 0 || $page['meta']['has_more']))<nav class="pagination" aria-label="Halaman pilihan WO">
            @if($page['meta']['offset'] > 0)<a class="button secondary small" href="{{ route('disruptions.work-orders', ['disruption'=>$event, 'wo_number'=>request('wo_number'), 'offset'=>max(0, $page['meta']['offset']-25)]) }}">Sebelumnya</a>@endif
            @if($page['meta']['has_more'])<a class="button secondary small" href="{{ route('disruptions.work-orders', ['disruption'=>$event, 'wo_number'=>request('wo_number'), 'offset'=>$page['meta']['offset']+25]) }}">Berikutnya</a>@endif
        </nav>@endif
    </section>
    <section class="panel detail-panel disruption-detail stack"><h2>Hubungan yang dicatat · {{ $activeLinks->count() }} aktif</h2>
        @forelse($activeLinks as $link)
            <details class="disruption-options" @if((int) old('link_id') === $link->id) open @endif>
                <summary>WO {{ $link->number() }} · {{ AssetDisruptionWorkOrder::STATES[$link->relation_state] }}</summary>
                <form class="stack" method="post" action="{{ route('disruptions.work-orders.update', [$event, $link]) }}">
                    @csrf @method('PUT')
                    <input type="hidden" name="link_id" value="{{ $link->id }}">
                    <input type="hidden" name="version" value="{{ (int) old('link_id') === $link->id ? old('version', $event->version) : $event->version }}">
                    <p><a class="text-link" href="{{ route('work-orders.show', ['ref'=>$link->work_order_ref, 'event'=>$link->record_ref, 'asset_ref'=>$link->asset_ref]) }}">Buka detail WO</a> · Identitas dicocokkan {{ $link->identity_checked_at->format('d M Y H:i:s') }} UTC, bukan jaminan freshness saat ini.</p>
                    <div><label for="state-{{ $link->id }}">Status hubungan</label><select id="state-{{ $link->id }}" name="relation_state" required>@foreach(AssetDisruptionWorkOrder::STATES as $value=>$label)<option value="{{ $value }}" @selected(((int) old('link_id') === $link->id ? old('relation_state', $link->relation_state) : $link->relation_state) === $value)>{{ $label }}</option>@endforeach</select></div>
                    <div><label for="note-{{ $link->id }}">Dasar / catatan hubungan</label><textarea id="note-{{ $link->id }}" name="note" rows="2" maxlength="2000">{{ (int) old('link_id') === $link->id ? old('note', $link->note) : $link->note }}</textarea></div>
                    <div><label for="reason-{{ $link->id }}">Alasan koreksi (wajib)</label><textarea id="reason-{{ $link->id }}" name="correction_reason" rows="2" required minlength="5" maxlength="2000">{{ (int) old('link_id') === $link->id ? old('correction_reason') : '' }}</textarea></div>
                    @if((int) old('link_id') === $link->id)<x-field-error name="relation_state" /><x-field-error name="note" /><x-field-error name="correction_reason" />@endif
                    <p class="field-hint">“Terkait menurut engineer” bukan validasi failure atau penyebab. “Hubungan dilepas” mempertahankan riwayat dan alasan perubahan.</p>
                    <button class="button secondary" type="submit">Simpan koreksi hubungan</button>
                </form>
            </details>
        @empty<p>Belum ada hubungan WO aktif. Ini bukan bukti bahwa kejadian tidak membutuhkan WO.</p>@endforelse
        @foreach($event->workOrders->where('relation_state', 'removed') as $link)<p class="field-hint">WO {{ $link->number() }} · hubungan dilepas. Riwayat ada pada jejak koreksi; pilih lagi di atas jika perlu menautkan ulang.</p>@endforeach
    </section>
</x-shell>

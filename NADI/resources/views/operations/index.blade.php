<x-shell title="Operasi" eyebrow="PROCESS WORKSPACE · DRAFT">
    <div class="section-intro"><p class="muted">Tampilan proses yang familiar untuk operator, pemeliharaan, dan engineering. Satu equipment, satu konteks bersama.</p><span class="badge neutral">Read only</span></div>
    <div class="operations-boundary"><strong>Historian belum terhubung</strong><p>Tampilan ini untuk konteks data dan aset, bukan pengganti HMI, alarm, atau kontrol DCS. Tidak ada nilai, kondisi operasi, maupun koneksi kontrol yang diasumsikan.</p></div>
    <div class="operations-layout">
        <section class="panel operations-equipment" aria-labelledby="equipment-heading">
            <div class="panel-heading"><h2 id="equipment-heading">Pilih equipment</h2><span class="badge neutral">Registry BSR / IP</span></div>
            <div class="operations-body">
                <p class="muted">Identitas aset dari Reliability Mart / Maximo. Pemilihan aset belum membuktikan pemetaan tag historian.</p>
                <form method="get" action="{{ route('operations') }}" class="stack operations-picker">
                    <div><label for="unit">Filter unit aset</label><input id="unit" name="unit" value="{{ $unit }}" maxlength="60" placeholder="Semua unit"><small class="field-hint">Ubah unit lalu tekan Muat daftar untuk memulai dari halaman pertama.</small></div>
                    <button type="submit" class="button secondary small">Muat daftar</button>
                </form>
                @if($page === null)
                    <div class="notice info"><strong>Daftar equipment belum terhubung</strong><p>Respons Registry belum dapat diverifikasi. Tidak ada equipment contoh yang ditambahkan.</p></div>
                @else
                    <form method="get" action="{{ route('operations') }}" class="stack operations-picker">
                        <input type="hidden" name="unit" value="{{ $unit }}"><input type="hidden" name="offset" value="{{ $offset }}">
                        <div><label for="equipment">Equipment terdaftar</label><select id="equipment" name="equipment"><option value="">Pilih equipment</option>
                            @if($selected && !in_array($selected['canonical_id'], array_column($page['items'], 'canonical_id'), true))<option value="{{ $selected['canonical_id'] }}" selected>{{ $selected['source_asset_number'] ?? $selected['canonical_id'] }} · Pilihan saat ini</option>@endif
                            @foreach($page['items'] as $asset)<option value="{{ $asset['canonical_id'] }}" @selected($equipment === $asset['canonical_id'])>{{ $asset['source_asset_number'] ?? $asset['canonical_id'] }} · {{ $asset['description'] ?? 'Deskripsi belum tersedia' }}</option>@endforeach
                        </select></div><button class="button primary" type="submit">Tampilkan equipment</button>
                    </form>
                    <div class="operations-pagination"><small class="muted">{{ count($page['items']) }} dari {{ number_format($page['meta']['total']) }} aset · halaman {{ intdiv($offset, 25) + 1 }}</small><div>
                        @if($offset > 0)<a class="text-link" href="{{ route('operations', ['unit'=>$unit,'offset'=>max(0,$offset-25),'equipment'=>$equipment]) }}">← Sebelumnya</a>@endif
                        @if($page['meta']['has_more'])<a class="text-link" href="{{ route('operations', ['unit'=>$unit,'offset'=>$offset+25,'equipment'=>$equipment]) }}">Berikutnya →</a>@endif
                    </div></div>
                @endif
            </div>
        </section>
        <section class="panel operations-canvas" aria-labelledby="canvas-heading">
            <div class="panel-heading"><h2 id="canvas-heading">Kanvas proses</h2><span class="badge neutral">Layout belum dipetakan</span></div>
            <div class="process-empty"><span class="process-mark" aria-hidden="true">▱</span><h2>Siapkan peta proses di sini</h2><p>Nama layar, simbol, hubungan proses, dan posisi nilai menunggu referensi Wonderware / Foxboro dari Anda. Belum ada diagram proses yang diverifikasi.</p><div class="process-value"><span>Nilai historian</span><strong>Belum terhubung</strong><small>Tag · satuan · waktu sumber · kualitas belum tersedia</small></div></div>
        </section>
    </div>
    <section class="panel operations-context" aria-labelledby="context-heading"><div class="panel-heading"><h2 id="context-heading">Konteks equipment</h2><span class="badge neutral">Identitas sumber</span></div><div class="operations-body">
        @if($selected)
            <div class="operations-selected"><div><p class="eyebrow">ASSET TERPILIH</p><h2>{{ $selected['source_asset_number'] ?? $selected['canonical_id'] }}</h2><p class="muted">{{ $selected['description'] ?? 'Deskripsi belum tersedia' }}</p></div><a class="button secondary small" href="{{ route('assets.show', $selected['canonical_id']) }}">Buka Master Asset →</a></div>
            <div class="operations-context-links"><a class="button secondary small" href="{{ route('work-orders.index', ['asset_ref'=>$selected['canonical_id']]) }}">Pemeliharaan · WO equipment →</a>@can('write-inspection-drafts')<a class="button secondary small" href="{{ route('inspections.create', ['asset_ref'=>$selected['canonical_id']]) }}">Engineering · Draft inspeksi →</a>@endcan</div><p class="data-note">Tautan pemeliharaan memakai identitas Asset yang sama. Draft inspeksi lokal belum menjadi analisis engineering tervalidasi; historian belum terhubung.</p>
            <dl class="operations-facts"><div><dt>Unit dari sumber</dt><dd>{{ $selected['unit'] ?? 'Belum tersedia' }}</dd></div><div><dt>Status record aset</dt><dd>{{ $selected['status'] ?? 'Belum tersedia' }}<small>Bukan status operasi realtime</small></dd></div><div><dt>Pemetaan historian</dt><dd>Belum diverifikasi</dd></div></dl>
        @elseif($selectionUnavailable)<p class="muted">Detail equipment belum terhubung atau identitas/scope belum dapat diverifikasi. Tidak ada data pengganti.</p>
        @else<p class="muted">Pilih equipment untuk melihat konteks Asset. Nilai historian tetap kosong sampai adapter dan pemetaan tag tersedia.</p>@endif
    </div></section>
    <section class="panel operations-reliability"><div class="panel-heading"><h2>Asset Wellness</h2><span class="badge neutral">Belum dinilai</span></div><div class="operations-body"><p class="muted">Warna perhatian equipment belum diterapkan. Status operasi, kualitas data historian, dan penilaian Asset Wellness merupakan konteks yang berbeda.</p><details><summary>Dasar warna dan alasan perhatian</summary><p>Ke depan, simbol dapat menunjukkan tingkat perhatian setelah definisi skor Asset Wellness, periode Pareto loss/gangguan, dan bukti pendukung divalidasi. Pengguna perlu dapat membuka alasan, periode, serta sumber data di balik warna.</p><p>Saat ini belum ada skor, Pareto loss, maupun kondisi sehat/sakit yang disimpulkan. Jumlah WO bukan jumlah kejadian gangguan tervalidasi; WAPPR tetap backlog terpisah.</p></details></div></section>
    <div class="operations-readiness"><div><span>01 · Layout proses</span><strong>Menunggu referensi</strong><p>Posisi equipment dan nilai akan dicocokkan bersama pengguna.</p></div><div><span>02 · Historian</span><strong>Adapter belum terhubung</strong><p>Tag, identitas, satuan, timestamp, dan kualitas perlu diverifikasi.</p></div><div><span>03 · Cache tampilan</span><strong>Belum aktif</strong><p>Pondasi baca per halaman dan cache RAM tersedia untuk simulasi terpisah. Historian nyata tetap belum aktif.</p></div></div>
    <p><a class="button secondary" href="{{ route('operations.historian') }}">Buka pondasi historian →</a></p>
</x-shell>

<x-shell title="Operasi" eyebrow="PROCESS WORKSPACE · DRAFT">
    <div class="ops-disclaimer"><p><b>Draft tampilan</b> · bukan pengganti HMI, alarm, atau kontrol DCS. Semua nilai masih placeholder.</p><span class="badge neutral">Read only</span></div>
    @php($contextQuery = array_filter(['unit' => $unit, 'offset' => $offset, 'equipment' => $equipment], fn ($value) => $value !== null && $value !== '' && $value !== 0))
    <nav class="ops-screen-navigation" aria-label="Layar proses draft">
        <div class="ops-screen-tabs">
            @foreach($screens as $screenCode)
                <a href="{{ route('operations', array_merge($contextQuery, ['screen' => $screenCode])) }}" @class(['ops-tab', 'active' => $screen === $screenCode]) @if($screen === $screenCode) aria-current="page" @endif>{{ $screenCode }}</a>
            @endforeach
        </div>
        <span class="ops-screen-status">{{ $screen === 'BOIL' ? 'Referensi visual tersedia · belum diverifikasi' : 'Menunggu referensi layar' }}</span>
    </nav>
    @if($screen === 'BOIL')
        @include('operations.boiler-draft')
        @include('operations.component-detail')
    @else
        @include('operations.screen-placeholder')
    @endif
    <details class="ops-registry" @if(request()->hasAny(['unit', 'offset', 'equipment'])) open @endif>
        <summary><span><strong>Konteks Asset Registry</strong> · daftar dan tautan existing, terpisah dari simbol draft</span></summary>
        <div class="ops-registry-content">
    <div class="operations-layout">
        <section class="panel operations-equipment" aria-labelledby="equipment-heading">
            <div class="panel-heading"><h2 id="equipment-heading">Pilih equipment</h2><span class="badge neutral">Registry BSR / IP</span></div>
            <div class="operations-body">
                <p class="muted">Identitas aset dari Reliability Mart / Maximo. Pemilihan aset belum membuktikan pemetaan tag historian.</p>
                <form method="get" action="{{ route('operations') }}" class="stack operations-picker">
                    <input type="hidden" name="screen" value="{{ $screen }}">
                    @if($draftComponent)<input type="hidden" name="component" value="{{ $draftComponent }}">@endif
                    <div><label for="unit">Filter unit aset</label><input id="unit" name="unit" value="{{ $unit }}" maxlength="60" placeholder="Semua unit"><small class="field-hint">Ubah unit lalu tekan Muat daftar untuk memulai dari halaman pertama.</small></div>
                    <button type="submit" class="button secondary small">Muat daftar</button>
                </form>
                @if($page === null)
                    <div class="notice info"><strong>Daftar equipment belum terhubung</strong><p>Respons Registry belum dapat diverifikasi. Tidak ada equipment contoh yang ditambahkan.</p></div>
                @else
                    <form method="get" action="{{ route('operations') }}" class="stack operations-picker">
                        <input type="hidden" name="screen" value="{{ $screen }}">
                        @if($draftComponent)<input type="hidden" name="component" value="{{ $draftComponent }}">@endif
                        <input type="hidden" name="unit" value="{{ $unit }}"><input type="hidden" name="offset" value="{{ $offset }}">
                        <div><label for="equipment">Equipment terdaftar</label><select id="equipment" name="equipment"><option value="">Pilih equipment</option>
                            @if($selected && !in_array($selected['canonical_id'], array_column($page['items'], 'canonical_id'), true))<option value="{{ $selected['canonical_id'] }}" selected>{{ $selected['source_asset_number'] ?? $selected['canonical_id'] }} · Pilihan saat ini</option>@endif
                            @foreach($page['items'] as $asset)<option value="{{ $asset['canonical_id'] }}" @selected($equipment === $asset['canonical_id'])>{{ $asset['source_asset_number'] ?? $asset['canonical_id'] }} · {{ $asset['description'] ?? 'Deskripsi belum tersedia' }}</option>@endforeach
                        </select></div><button class="button primary" type="submit">Tampilkan equipment</button>
                    </form>
                    <div class="operations-pagination"><small class="muted">{{ count($page['items']) }} dari {{ number_format($page['meta']['total']) }} aset · halaman {{ intdiv($offset, 25) + 1 }}</small><div>
                        @if($offset > 0)<a class="text-link" href="{{ route('operations', ['screen'=>$screen,'component'=>$draftComponent,'unit'=>$unit,'offset'=>max(0,$offset-25),'equipment'=>$equipment]) }}">← Sebelumnya</a>@endif
                        @if($page['meta']['has_more'])<a class="text-link" href="{{ route('operations', ['screen'=>$screen,'component'=>$draftComponent,'unit'=>$unit,'offset'=>$offset+25,'equipment'=>$equipment]) }}">Berikutnya →</a>@endif
                    </div></div>
                @endif
            </div>
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
    <section class="panel operations-reliability"><div class="panel-heading"><h2>Asset Wellness</h2><span class="badge neutral">Belum dinilai</span></div><div class="operations-body"><p class="muted">Warna contoh pada diagram hanya pratinjau visual, bukan penilaian kondisi aset. Status operasi, kualitas data historian, dan penilaian Asset Wellness merupakan konteks yang berbeda.</p><details><summary>Dasar warna dan alasan perhatian</summary><p>Simbol dapat menunjukkan tingkat perhatian setelah definisi skor Asset Wellness, periode Pareto loss/gangguan, dan bukti pendukung divalidasi. Pengguna perlu dapat membuka alasan, periode, serta sumber data di balik warna.</p><p>Diagram draft ini belum memakai skor, Pareto loss, maupun kesimpulan kondisi sehat/sakit. Jumlah WO bukan jumlah kejadian gangguan tervalidasi; WAPPR tetap backlog terpisah.</p></details></div></section>
    <div class="operations-readiness"><div><span>01 · Layout proses</span><strong>{{ $screen === 'BOIL' ? 'Draft visual tersedia' : 'Referensi belum tersedia' }}</strong><p>{{ $screen === 'BOIL' ? 'Susunan mengikuti referensi; jalur dan identitas belum diverifikasi.' : 'Diagram dan parameter tidak ditampilkan sebelum referensi diverifikasi.' }}</p></div><div><span>02 · Historian</span><strong>Adapter belum terhubung</strong><p>Tag, identitas, satuan, timestamp, dan kualitas perlu diverifikasi.</p></div><div><span>03 · Cache tampilan</span><strong>Belum aktif</strong><p>Pondasi baca per halaman dan cache RAM tersedia untuk simulasi terpisah. Historian nyata tetap belum aktif.</p></div></div>
    <p><a class="button secondary" href="{{ route('operations.historian') }}">Buka pondasi historian →</a></p>

        </div>
    </details>
</x-shell>

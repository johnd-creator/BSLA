<x-shell title="Timeline aset" eyebrow="KONTEKS LINTAS SUMBER · READ ONLY">
    <a class="back-link" href="{{ route('assets.show', $asset) }}">← Detail Asset</a>
    @if($record === null)
        <section class="panel connection-state"><h2>Aset belum terverifikasi</h2><p>Identitas aset belum dapat dibaca dari Mart. Timeline tidak dimuat agar data tidak tercampur.</p><a class="button secondary" href="{{ request()->url() }}">Muat ulang</a></section>
    @else
        <section class="panel detail-panel timeline-intro">
            <div><h2>{{ $record['source_asset_number'] ?? $record['canonical_id'] }}</h2><p>{{ $record['description'] ?? 'Deskripsi belum tersedia.' }}</p><p class="data-note">{{ $record['site_code'] }} / {{ $record['organization_code'] }} · {{ $record['unit'] ?? 'Unit belum tersedia' }} · Identitas aset persis, tanpa penggabungan alias.</p></div>
            <nav class="timeline-links" aria-label="Riwayat aset lengkap"><a class="button secondary" href="{{ route('work-orders.index', ['asset_ref'=>$asset]) }}">Riwayat WO</a><a class="button secondary" href="{{ route('pdm.history', ['asset_ref'=>$asset]) }}">Riwayat PdM lokal</a><a class="button secondary" href="{{ route('disruptions.index', ['asset_ref'=>$asset]) }}">Log gangguan aset</a></nav>
        </section>
        <section class="panel detail-panel" aria-labelledby="timeline-coverage">
            <h2 id="timeline-coverage">Cakupan cuplikan</h2>
            <p class="data-note">{{ $record['registered'] ? 'Maksimal 5 record per domain dari konteks Mart' : 'Maksimal 25 WO dari inventaris' }}, 25 pengukuran PdM lokal dan 25 log gangguan manual. Urutan waktu berlaku pada cuplikan ini, bukan seluruh riwayat. Angka di bawah hanya jumlah record yang ditampilkan.</p>
            <ul class="timeline-sources">
                @foreach(\App\Services\AssetTimeline::LABELS as $source => $label)
                    <li><strong>{{ $label }}</strong><span>{{ match($preview['states'][$source]) { 'available' => $preview['counts'][$source].' record pada cuplikan', 'empty' => 'Belum ada record pada respons', 'registry_required' => 'Memerlukan Registry', default => 'Belum terhubung / respons tidak valid' } }}</span></li>
                @endforeach
            </ul>
            <p class="data-note">FMEA, kondisi aset, dan overhaul hanya tampil bila tersedia serta tertaut ke aset melalui Mart. Tidak ada record bukan bukti aset sehat atau tidak pernah mengalami gangguan. Overhaul tanpa relasi aset tidak disimpulkan dari nama/WO. PdM tetap draft lokal, belum tervalidasi. Log gangguan memakai keanggotaan aset persis, bukan pewarisan hierarki; catatan dibatalkan tetap terlihat sebagai histori.</p>
        </section>
        <section class="panel detail-panel" aria-labelledby="timeline-events">
            <div class="timeline-heading"><h2 id="timeline-events">Kronologi cuplikan</h2><span class="muted">Waktu berzona ditampilkan dalam WIB (UTC+7); tanggal saja tanpa konversi zona</span></div>
            @if(count($preview['events']))
                <ol class="asset-timeline">
                    @foreach($preview['events'] as $event)
                        <li>
                            <div class="timeline-date">@if($event['date_only'] ?? null)<time datetime="{{ $event['date_only'] }}">{{ \Carbon\CarbonImmutable::createFromFormat('!Y-m-d', $event['date_only'])->format('d M Y') }}</time>@elseif($event['at'])<time datetime="{{ $event['at']->toIso8601String() }}">{{ $event['at']->setTimezone('Asia/Jakarta')->format('d M Y H:i:s') }}</time>@else<span>Tanpa waktu terverifikasi</span>@endif<small>{{ $event['basis'] }}</small></div>
                            <div class="timeline-event"><div class="timeline-event-heading"><span class="source-pill">{{ \App\Services\AssetTimeline::LABELS[$event['source']] }}</span><span class="muted">{{ $event['status'] }}</span></div><h3>{{ $event['title'] }}</h3><p class="data-note">{{ $event['note'] }}</p><details class="timeline-reference"><summary>Referensi record</summary><p>{{ $event['reference'] }}</p></details>@if($event['url'])<a class="text-link" href="{{ $event['url'] }}">{{ $event['link_label'] }} →</a>@endif</div>
                        </li>
                    @endforeach
                </ol>
            @else
                <p class="board-empty">Belum ada record yang dapat ditampilkan. Periksa status tiap sumber di atas; sumber yang gagal tidak dihitung sebagai nol.</p>
            @endif
        </section>
        <p class="data-note">Catatan tanggal saja ditampilkan setelah catatan berjam pada tanggal yang sama, bukan bukti urutan kejadian dalam hari tersebut. Pengukuran berkala tidak berarti data harian atau pemantauan realtime. Tanggal record bukan kesegaran sinkronisasi. Tanggal rencana bukan waktu pelaksanaan. Timeline ini tidak menghitung incident count, skor Asset Wellness, atau availability.</p>
    @endif
</x-shell>

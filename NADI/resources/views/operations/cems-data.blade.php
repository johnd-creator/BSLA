@if(!$snapshot)
    <section class="panel cems-empty"><h2>CEMS belum tersedia</h2><p>Layanan live belum diaktifkan atau tidak dapat dibaca. Tidak ada nilai PLC yang diklaim tersedia.</p><p class="muted">Konfigurasi endpoint cache RAM dan koneksi sumber perlu diverifikasi. Tidak ada fallback ke database historis.</p></section>
@else
    @php($signalsByParameter = collect($signals['signals'] ?? [])->keyBy('parameter_code'))
    @if($snapshot['source_mode'] === 'simulation')<div class="operations-boundary cems-simulation"><strong>SIMULASI · BUKAN DATA PLC</strong><p>Nilai berikut berasal dari sumber simulasi untuk pengujian, bukan pengukuran operasional.</p></div>@endif
    <section class="panel cems-status" data-cems-stack="{{ $snapshot['stack_id'] }}">
        <div class="panel-heading"><h2>Cerobong {{ $snapshot['stack_id'] }}</h2><span class="badge neutral">{{ $snapshot['source_mode'] === 'plc' ? 'Sumber PLC' : 'SIMULASI' }} · {{ $snapshot['status'] }}</span></div>
        <div class="cems-process">
            <svg class="cems-stack-illustration" viewBox="0 0 520 360" role="img" aria-labelledby="stack-title stack-desc">
                <title id="stack-title">Ilustrasi teknis satu cerobong dan analyzer CEMS</title>
                <desc id="stack-desc">Skema konseptual satu cerobong dengan akses tangga, probe sampling dan jalur sampel menuju kabinet analyzer. Bukan gambar as-built, indikator operasi, atau verifikasi konfigurasi lapangan.</desc>
                <defs>
                    <pattern id="cems-grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#dce7ee" stroke-width="0.7"/></pattern>
                    <linearGradient id="cems-shell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a7bdcc"/><stop offset="0.42" stop-color="#f0f6f9"/><stop offset="0.72" stop-color="#d6e3ec"/><stop offset="1" stop-color="#91aabb"/></linearGradient>
                    <linearGradient id="cems-cabinet" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f6fbfc"/><stop offset="1" stop-color="#d4e5eb"/></linearGradient>
                    <marker id="cems-flow-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#6c8d9f"/></marker>
                </defs>
                <rect x="1" y="1" width="518" height="358" rx="14" fill="#f5f9fb" stroke="#d5e2ea"/>
                <rect x="12" y="12" width="496" height="308" fill="url(#cems-grid)"/>
                <text x="24" y="31" fill="#4b677b" font-size="11" font-weight="600" letter-spacing="1.4">ILUSTRASI KONSEPTUAL</text>
                <path d="M29 306H490" stroke="#a8bcc9" stroke-width="2"/>
                <rect x="80" y="298" width="155" height="9" rx="2" fill="#839dab"/>
                <path d="M102 298L117 63H182L197 298Z" fill="url(#cems-shell)" stroke="#58768c" stroke-width="2"/>
                <ellipse cx="149.5" cy="63" rx="32.5" ry="8" fill="#58768c"/>
                <ellipse cx="149.5" cy="62" rx="25" ry="4.5" fill="#c7d7e2"/>
                <path d="M112 126Q150 135 186 126M108 194Q150 204 190 194M105 261Q150 272 194 261" fill="none" stroke="#8da6b7" stroke-width="2"/>
                <path d="M150 265V222M150 193V150M150 123V82" fill="none" stroke="#6c8d9f" stroke-width="2" marker-end="url(#cems-flow-arrow)"/>
                <path d="M211 291V88M222 291V88M211 97H222M211 111H222M211 125H222M211 139H222M211 153H222M211 167H222M211 181H222M211 195H222M211 209H222M211 223H222M211 237H222M211 251H222M211 265H222M211 279H222" fill="none" stroke="#718d9e" stroke-width="2"/>
                <path d="M184 182H243V166M185 165H243M235 165V182M194 181V165" fill="none" stroke="#58768c" stroke-width="2"/>
                <path d="M168 152H202" stroke="#087879" stroke-width="5"/><circle cx="187" cy="152" r="6" fill="#e2f4f0" stroke="#087879" stroke-width="2"/>
                <path d="M202 152H291V217H350" fill="none" stroke="#087879" stroke-width="3" stroke-dasharray="7 4"/>
                <path d="M248 152L240 148V156Z" fill="#087879"/>
                <path d="M240 102H224L195 143M103 230H52L42 215" fill="none" stroke="#91a8b8" stroke-width="1.2"/>
                <text x="239" y="89" fill="#243e52" font-size="12" font-weight="600">Probe sampling</text>
                <text x="23" y="206" fill="#506d81" font-size="11">Badan</text><text x="23" y="220" fill="#506d81" font-size="11">cerobong</text>
                <text x="306" y="168" fill="#087879" font-size="11">Jalur sampel</text>
                <rect x="350" y="184" width="124" height="111" rx="6" fill="url(#cems-cabinet)" stroke="#58768c" stroke-width="2"/>
                <path d="M350 204H474M363 214V280M462 214V280" stroke="#b5c9d5" fill="none"/>
                <rect x="376" y="216" width="72" height="27" rx="3" fill="#244756"/>
                <path d="M384 229H399M405 229H440" stroke="#9dcacb" stroke-width="2"/>
                <rect x="376" y="252" width="72" height="25" rx="3" fill="#edf5f7" stroke="#b0c7d3"/>
                <path d="M384 260H421M384 267H421" stroke="#91aebc" stroke-width="2"/><circle cx="437" cy="264" r="3" fill="#a7bdc9"/>
                <path d="M360 295V305M464 295V305" stroke="#58768c" stroke-width="4"/>
                <text x="412" y="198" text-anchor="middle" fill="#243e52" font-size="10" font-weight="600" letter-spacing="1">CEMS</text>
                <text x="149" y="332" text-anchor="middle" fill="#243e52" font-size="13" font-weight="600">Satu cerobong</text>
                <text x="412" y="332" text-anchor="middle" fill="#243e52" font-size="13" font-weight="600">Analyzer CEMS</text>
                <text x="260" y="349" text-anchor="middle" fill="#6d8393" font-size="10">Tidak berskala · posisi dan sambungan belum diverifikasi</text>
            </svg>
            <div class="cems-scope">
                <strong class="cems-scope-title">1 cerobong · {{ count($snapshot['parameters']) }} parameter</strong>
                <p>Seluruh parameter di bawah berasal dari cerobong ini. Setiap kartu menggabungkan nilai pengukuran, kualitas data, tautan KKS, dan feed sinyal per menit.</p>
                <h3>Skema CEMS 2D</h3><p class="data-note">Ilustrasi alur pengukuran, bukan gambar teknik/as-built. Posisi dan sambungan aktual belum diverifikasi.</p>
                <p class="data-note">Sinyal diterima berarti ada data pengukuran, bukan bukti alat beroperasi, sehat, atau tidak rusak. Tidak mengubah status WO, MTBF, MTTR, atau downtime.</p>
            </div>
        </div>
        <dl class="cems-facts"><div><dt>Siklus sumber terakhir</dt><dd>{{ $snapshot['last_cycle_at'] ?? 'Belum ada' }}</dd></div><div><dt>Snapshot cache</dt><dd>{{ $snapshot['generated_at'] }}</dd></div><div><dt>Cache dimulai</dt><dd>{{ $snapshot['cache_started_at'] }}</dd></div><div><dt>Sampel dalam RAM</dt><dd>{{ $snapshot['samples_retained'] }}</dd></div></dl>
        <p class="data-note">Timestamp menyertakan zona waktu sumber. Kualitas dan umur tiap parameter dapat berbeda. Angka terakhir yang tidak berkualitas good bukan nilai live terverifikasi.</p>
    </section>
    <section class="cems-parameters" aria-labelledby="cems-parameters-title">
        <div class="cems-parameters-heading"><h2 id="cems-parameters-title">Parameter cerobong {{ $snapshot['stack_id'] }}</h2><span class="badge neutral">Satu set pengukuran</span></div>
        @if($signals === null)<p class="data-note">Feed per menit belum tersedia.</p>@else
            <p class="data-note">Feed sinyal per menit: {{ $signals['status'] }} · dibuat {{ $signals['generated_at'] ?? 'belum ada' }} · umur {{ $signals['feed_age_seconds'] === null ? 'tidak diketahui' : number_format($signals['feed_age_seconds'], 1).' detik' }}. Ringkasan data yang sama, bukan cerobong tambahan.</p>
        @endif
        <div class="cems-cards">
            @forelse($snapshot['parameters'] as $row)
                @php($signal = $signalsByParameter->get($row['parameter_code']))
                <article class="panel cems-card" data-cems-parameter="{{ $row['parameter_code'] }}" data-cems-quality="{{ $row['quality'] }}" data-cems-observed-at="{{ $row['observed_at'] ?? '' }}" data-cems-age-seconds="{{ $row['age_seconds'] ?? '' }}">
                    <div class="cems-card-heading"><span class="eyebrow">{{ $row['parameter_code'] }}</span><span class="badge neutral">{{ $row['quality'] }}</span></div>
                    <h3>{{ $row['name'] }}</h3>
                    <p class="cems-value">{{ \App\Services\CemsLive::formatValue($row['value_final']) }} <small>{{ $row['unit'] }}</small></p>
                    <p class="muted">Umur: {{ $row['age_seconds'] === null ? 'tidak diketahui' : number_format($row['age_seconds'], 1).' detik' }}</p>
                    <div class="cems-card-feed" data-cems-feed="{{ $row['parameter_code'] }}">
                        <strong>Feed data · 1 menit</strong>
                        @if($signal)
                            <span>{{ $signal['signal_state'] === 'receiving' ? 'Ada sampel baik di jendela feed' : 'Tidak ada sampel baik terbaru' }}</span>
                            <small>{{ $signal['good_samples_last_minute'] }} / {{ $signal['expected_samples_per_minute'] }} sampel baik dalam 60 detik</small>
                            <small>Terakhir diterima: {{ $signal['last_received_at'] ?? 'belum ada' }}</small>
                        @else<small>Belum tersedia untuk parameter ini.</small>@endif
                    </div>
                    <div class="cems-card-asset">@if(isset($assetLinks[$row['parameter_code']]))<a class="text-link" href="{{ route('assets.show', $assetLinks[$row['parameter_code']]['canonical_id']) }}">KKS {{ $assetLinks[$row['parameter_code']]['kks'] }} → detail aset</a>@else<small class="muted">KKS belum dipetakan / belum terverifikasi</small>@endif</div>
                    <small>Observasi: {{ $row['observed_at'] ?? 'Belum ada' }}</small><small>Terakhir baik: {{ $row['last_good_at'] ?? 'Belum ada' }}</small>
                </article>
            @empty<p class="muted">Belum ada parameter dalam cache.</p>@endforelse
        </div>
    </section>
    <section class="panel cems-history"><div class="panel-heading"><h2>Riwayat ringkas · maksimum 6 jam</h2></div>
        @if($parameter !== null)<form method="get" action="{{ route('operations.cems') }}" data-cems-filter><label for="cems-parameter">Parameter</label><select id="cems-parameter" name="parameter">@foreach($snapshot['parameters'] as $row)<option value="{{ $row['parameter_code'] }}" @selected($parameter === $row['parameter_code'])>{{ $row['name'] }} ({{ $row['unit'] }})</option>@endforeach</select><button class="button secondary small" type="submit">Tampilkan</button></form>@endif
        <p class="data-note">Maksimum 360 titik dari jendela RAM, bukan arsip lengkap atau nilai rata-rata. Nilai kosong bukan nol; kualitas setiap titik tetap ditampilkan.</p>
        @if($history === null)<p class="muted">Riwayat belum tersedia atau gagal dibaca.</p>
        @elseif(count($history['points']) === 0)<p class="muted">Belum ada sampel untuk parameter ini.</p>
        @else
            @if($history['truncated'])<p class="data-note">Riwayat diringkas oleh layanan; tidak semua titik 5 detik ditampilkan.</p>@endif
            <div class="table-wrap cems-history-scroll"><table><thead><tr><th>Waktu observasi</th><th>Nilai</th><th>Kualitas</th></tr></thead><tbody>@foreach(array_reverse($history['points']) as $point)<tr><td>{{ $point['observed_at'] }}</td><td>{{ \App\Services\CemsLive::formatValue($point['value_final']) }}</td><td>{{ $point['quality'] }}</td></tr>@endforeach</tbody></table></div>
        @endif
    </section>
@endif

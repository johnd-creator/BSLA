<x-shell title="Jejak perhitungan reliability" eyebrow="PILOT · PEMBILANG · PENYEBUT · EXCLUSIONS">
    <a class="back-link" href="{{ isset($snapshot) ? route('reliability.snapshots.show',$snapshot) : route('reliability.index',['asset_ref'=>$report['asset_ref'], ...\App\Services\ReliabilityPeriod::fromReport($report)->query()]) }}">← Laporan reliability</a>
    <section class="panel reliability-panel detail-panel">
        <h2>{{ $report['asset_ref'] }} · {{ $report['period']['label'] ?? $report['period']['year'] }}</h2>
        <p>{{ isset($snapshot) ? 'Jejak ini berasal dari snapshot immutable #'.$snapshot->id.'. Tidak dihitung ulang menggunakan aturan terbaru.' : 'Jejak berdasarkan evidence lokal terkini. Simpan snapshot dari laporan untuk mengunci basis review.' }}</p>
        <ol><li>Periksa aturan dan scope fungsi.</li><li>Rekonsiliasi setiap episode serta interval operasi di bawah.</li><li>Simpan paket snapshot untuk review. Pengesahan resmi tetap merupakan keputusan organisasi yang belum dikonfigurasi.</li></ol>
    </section>
    @if(!isset($report['calculation']))
        <section class="panel reliability-panel detail-panel"><p>Snapshot lama ini belum menyimpan jejak mesin hitung. Bukti aslinya tetap dapat dibaca/diunduh; tidak diganti dengan perhitungan baru.</p></section>
    @else
        @include('reliability.calculation-card')
        <section class="panel reliability-panel detail-panel" id="calculation-events">
            <h2>Episode, numerator & alasan eksklusi</h2>
            <form method="get" class="form-grid">
                @unless(isset($snapshot))<input type="hidden" name="asset_ref" value="{{ $report['asset_ref'] }}">@include('reliability.period-hidden')@endunless
                <div><label for="trace_metric">Populasi trace</label><select id="trace_metric" name="trace_metric">
                    @foreach(['all'=>'Semua bukti kejadian','count'=>'Failure eligible lokal','active_repair'=>'Episode repair lengkap','restoration'=>'Episode restoration lengkap','excluded'=>'Episode dikeluarkan'] as $value=>$label)<option value="{{ $value }}" @selected(($filters['trace_metric'] ?? 'all')===$value)>{{ $label }}</option>@endforeach
                </select></div>
                @if(isset($report['trends']['period_months']))<div><label for="trace_period_month">Bulan onset WIB</label><select id="trace_period_month" name="trace_period_month"><option value="">Semua bulan</option>@foreach($report['trends']['period_months'] as $m)<option value="{{ $m }}" @selected(($filters['trace_period_month'] ?? null)===$m)>{{ $m }}</option>@endforeach</select></div>@else<div><label for="trace_month">Bulan onset WIB</label><select id="trace_month" name="trace_month"><option value="">Semua bulan/tanggal belum diketahui</option>@for($i=1;$i<=12;$i++)<option value="{{ $i }}" @selected((int)($filters['trace_month'] ?? 0)===$i)>{{ $i }}</option>@endfor</select></div>
                @endif
<div class="form-actions"><button class="button secondary">Saring trace</button></div>
            </form>
            <p class="data-note">Filter hanya mengubah tabel, bukan hasil hitung atau snapshot. {{ $traceRows->total() }} record sesuai filter, 20 per halaman. Link review membuka kondisi terkini, bukan mengubah snapshot.</p>
            <div class="table-wrap table-scroll" tabindex="0"><table><thead><tr><th>Episode & versi</th><th>Onset → kembali siap</th><th>Kontribusi numerator</th><th>Keputusan / evidence</th></tr></thead><tbody>
            @forelse($traceRows as $row)
                <tr><td><a class="text-link" href="{{ route('reliability.reviews',[$row['event_id'],'asset_ref'=>$report['asset_ref']]) }}">{{ $row['reference'] }}</a><small>Event v{{ $row['event_version'] }} · review {{ $row['review_revision'] ?? 'belum ada' }} · {{ $row['review_rule_version'] ?? 'belum ada rule' }}</small><small>Reviewer {{ $row['reviewer_id'] ?? 'belum ada' }} · {{ $row['reviewed_at'] ?? 'belum direview' }}</small></td>
                <td>{{ $row['onset'] ?? 'Onset belum diketahui' }} → {{ $row['restored_at'] ?? 'Kembali siap belum diketahui' }}</td>
                <td>Failure count lokal: {{ $row['eligible_failure'] ? '1' : 'dikeluarkan' }}<small>Onset/exposure MTBF: {{ $row['mtbf_exposure_eligible'] ? 'sesuai segmen '.implode(', ', $row['matched_exposure_segments']) : 'belum eligible' }}</small><small>Repair: {{ $row['active_repair_seconds'] === null ? 'Tidak eligible / belum lengkap' : $row['active_repair_seconds'].' detik' }}</small><small>Restoration: {{ $row['restoration_seconds'] === null ? 'Tidak eligible / belum lengkap' : $row['restoration_seconds'].' detik' }}</small></td>
                <td>{{ $row['eligible_failure'] ? 'Review failure berlaku, scope onset sesuai' : implode(' · ',$row['exclusion_reasons']) }}<details><summary>Fungsi, interval & sumber</summary><p>{{ $row['required_function'] ?? 'Belum dicatat' }}</p><p>{{ $row['evidence'] ?? 'Belum ada evidence' }}</p><p>{{ $row['timing_evidence'] ?? 'Batas waktu belum dibuktikan' }}</p><ul>@foreach($row['active_intervals'] as $interval)<li>{{ $interval['start'] }} → {{ $interval['end'] }} · {{ $interval['seconds'] }} detik</li>@endforeach</ul><p class="data-note">{{ count($row['work_orders']) }} relasi WO sebagai konteks, tidak menjadi denominator.</p></details></td></tr>
            @empty<tr><td colspan="4">Tidak ada record sesuai filter. Tidak menyatakan nol failure operasional.</td></tr>@endforelse
            </tbody></table></div>{{ $traceRows->links() }}
        </section>
        <section class="panel reliability-panel detail-panel" id="calculation-exposure">
            <h2>Jejak exposure, bukan jam kalender</h2>
            <p class="data-note">{{ $exposureRows->total() }} segmen, 20 per halaman. Jendela half-open dipotong tepat ke periode WIB; STOP/UNKNOWN/gap/overlap tidak menjadi runtime. Log yang ditautkan membuka revisi terkini; versi bukti yang dihitung tersedia dalam JSON snapshot.</p>
            <div class="table-wrap table-scroll" tabindex="0"><table><thead><tr><th>Awal → akhir</th><th>Status</th><th>Detik eligible</th><th>Log sumber / eksklusi</th></tr></thead><tbody>
            @foreach($exposureRows as $segment)<tr><td>{{ $segment['start'] }} → {{ $segment['end'] }}</td><td>{{ $segment['state'] }}</td><td>{{ $segment['eligible_seconds'] }}</td><td>@foreach($segment['log_ids'] as $id)<a class="text-link" href="{{ route('reliability.operating.show',$id) }}">Log #{{ $id }}</a> @endforeach<small>{{ $segment['exclusion_reason'] ?? 'Masuk numerator exposure' }}</small></td></tr>@endforeach
            </tbody></table></div>{{ $exposureRows->links() }}
            <p class="data-note">Basis {{ $report['calculation']['basis_hash'] }}. Jejak lengkap dan record sumber berversi tersedia di unduhan JSON.</p>
        </section>
    @endif
</x-shell>

@if(isset($report['trends']))
<section class="panel reliability-panel detail-panel" id="reliability-trends">
    <h2>Tren & Pareto failure yang direview</h2>
    <p>Exact asset/periode, review berlaku, onset tepat. WO, duplikat, review kedaluwarsa dan konflik episode tidak dijadikan failure baru. Pareto memakai jenis observasi, bukan akar penyebab yang diasumsikan.</p>
    @if(isset($trendView))
    <form method="get" class="form-grid" action="{{ isset($snapshot) ? route('reliability.snapshots.show',$snapshot) : route('reliability.index') }}#reliability-trends">
        @unless(isset($snapshot))<input type="hidden" name="asset_ref" value="{{ $report['asset_ref'] }}">@include('reliability.period-hidden')@endunless
        <div><label for="trend_basis">Ukuran tren / Pareto</label><select id="trend_basis" name="trend_basis">@foreach(\App\Services\ReviewedFailureTrends::BASES as $value=>$label)<option value="{{ $value }}" @selected($trendFilters['trend_basis']===$value)>{{ $label }}</option>@endforeach</select></div>
        @if(isset($report['trends']['period_months']))<div><label for="trend_period_month">Bulan onset WIB</label><select id="trend_period_month" name="trend_period_month"><option value="">Semua bulan</option>@foreach($report['trends']['period_months'] as $m)<option value="{{ $m }}" @selected(($trendFilters['trend_period_month'] ?? null)===$m)>{{ $m }}</option>@endforeach</select></div>@else<div><label for="trend_month">Bulan onset WIB</label><select id="trend_month" name="trend_month"><option value="">Semua bulan</option>@for($i=1;$i<=12;$i++)<option value="{{ $i }}" @selected($trendFilters['trend_month']===$i)>{{ $i }}</option>@endfor</select></div>
        @endif
<div class="form-actions"><button class="button secondary">Tampilkan tren</button></div>
    </form>
    <p class="data-note">Filter hanya mengubah visual/tabel ini. Perhitungan, evidence hash dan snapshot tidak berubah. Ukuran aktif: {{ $trendView['label'] }}.</p>
    @if($trendView['status']==='PARTIAL_WITHHELD')<p class="notice error">Bukti parsial. Tren/Pareto ditahan.</p>
    @elseif($trendView['status']==='INSUFFICIENT_DATA')<p class="notice">Data belum cukup untuk ukuran/filter ini. Tidak ada angka KPI atau kejadian yang dibuat.</p>
    @else
    @php
        $traceRoute=isset($snapshot) ? 'reliability.snapshots.calculation' : 'reliability.calculation';
        $traceScope=isset($snapshot) ? ['snapshot'=>$snapshot] : ['asset_ref'=>$report['asset_ref'], ...\App\Services\ReliabilityPeriod::fromReport($report)->query()];
    @endphp
    <div class="reliability-readiness-grid">
        <div><h3>Tren bulanan · {{ $trendView['unit'] }}</h3>
            @if(count($trendView['months']) <= 24)
            <svg class="reliability-chart" viewBox="0 0 {{ max(600, count($trendView['months'])*60+50) }} 245" role="img" aria-label="Tren bulanan {{ $trendView['label'] }}; nilai dan evidence tersedia pada tabel">
                <line x1="35" y1="180" x2="{{ max(590, count($trendView['months'])*60+40) }}" y2="180" stroke="currentColor" />
                @foreach($trendView['months'] as $month)
                @php $height=140*$month['value']/$trendView['max_month']; $x=40+$loop->index*60; @endphp
                <rect x="{{ $x }}" y="{{ 180-$height }}" width="28" height="{{ $height }}" fill="#0b7378"><title>Bulan {{ $month['period_month'] ?? $month['month'] }}: {{ number_format($month['value'],3,',','.') }} {{ $trendView['unit'] }} / {{ $month['episodes'] }} episode</title></rect>
                <text x="{{ $x+14 }}" y="200" text-anchor="middle">{{ $month['month'] }}</text>
                @isset($month['period_month'])<text x="{{ $x+14 }}" y="228" text-anchor="middle">{{ substr($month['period_month'],0,4) }}</text>@endisset
                @endforeach
            </svg>
            @else<p class="data-note">Rentang melebihi 24 bulan. Gunakan tabel bulanan agar tahun dan angka tetap terbaca.</p>@endif
            <div class="table-wrap table-scroll" tabindex="0"><table><thead><tr><th>Bulan WIB</th><th>{{ $trendView['unit'] }}</th><th>Episode / evidence</th></tr></thead><tbody>
            @foreach($trendView['months'] as $month)
            @if(($trendView['period_month'] ?? null) ? $month['period_month']===$trendView['period_month'] : ($trendView['month']===null || $month['month']===$trendView['month']))
            <tr><td>{{ $month['period_month'] ?? $report['period']['year'].'-'.str_pad($month['month'],2,'0',STR_PAD_LEFT) }}</td><td>{{ $trendView['basis']==='count' ? $month['value'] : number_format($month['value'],3,',','.') }}</td><td>@if($month['episodes'])<a class="text-link" href="{{ route($traceRoute,[...$traceScope,'trace_metric'=>$trendView['basis'],...(isset($month['period_month']) ? ['trace_period_month'=>$month['period_month']] : ['trace_month'=>$month['month']])]) }}">{{ $month['episodes'] }} episode · telusuri</a>@else 0 record eligible @endif</td></tr>
            @endif
            @endforeach
            </tbody></table></div>
        </div>
        <div><h3>Pareto jenis observasi · {{ $trendView['unit'] }}</h3>
            <svg class="reliability-chart" viewBox="0 0 600 {{ max(100,count($trendView['pareto'])*52+20) }}" role="img" aria-label="Pareto jenis observasi berdasarkan {{ $trendView['label'] }}; rincian ada pada tabel">
            @foreach($trendView['pareto'] as $item)
            <text x="8" y="{{ 25+$loop->index*52 }}">{{ \App\Models\AssetDisruption::TYPES[$item['category']] ?? $item['category'] }}</text>
            <rect x="140" y="{{ 8+$loop->index*52 }}" width="{{ 340*$item['value']/$trendView['max_category'] }}" height="24" fill="#0b7378" />
            <text x="490" y="{{ 25+$loop->index*52 }}">{{ $item['cumulative_percent'] === null ? '—' : $item['cumulative_percent'].'%' }}</text>
            @endforeach
            </svg>
            <div class="table-wrap table-scroll" tabindex="0"><table><thead><tr><th>Jenis</th><th>{{ $trendView['unit'] }}</th><th>Episode</th><th>Kumulatif</th></tr></thead><tbody>
            @foreach($trendView['pareto'] as $item)<tr><td>{{ \App\Models\AssetDisruption::TYPES[$item['category']] ?? $item['category'] }}</td><td>{{ $trendView['basis']==='count' ? $item['value'] : number_format($item['value'],3,',','.') }}</td><td>{{ $item['count'] }}</td><td>{{ $item['cumulative_percent'] === null ? 'Tidak terdefinisi: total durasi nol' : $item['cumulative_percent'].'%' }}</td></tr>@endforeach
            </tbody></table></div>
        </div>
    </div>
    @endif
    <p class="data-note">{{ $trendView['included_episodes'] }} episode masuk ukuran ini · {{ $trendView['excluded_incomplete'] }} episode dikeluarkan karena durasi belum lengkap/tidak berlaku. {{ $report['trends']['excluded_missing_onset'] }} onset belum tepat · {{ $report['trends']['excluded_conflicting_episodes'] ?? 0 }} konflik/recurrence belum terselesaikan dikeluarkan. Durasi memakai episode utuh periode onset, bukan downtime kalender. Sampel lengkap bisa bias; nol record bukan bukti nol failure operasional.</p>
    @else
    <p class="notice">Snapshot lama menyimpan ringkasan tren sebelumnya, tanpa trace untuk visual baru. Tidak dihitung ulang dari data terkini.</p>
    <p>{{ $report['trends']['reviewed_count'] ?? 'Belum tersedia' }} record lokal direview dalam ringkasan lama. Unduh evidence snapshot untuk rincian aslinya.</p>
    @endif
</section>
@endif

<dl class="overview-metrics">
    @foreach($snapshot['metrics'] as $metric)
        <div class="panel overview-metric" data-metric="{{ $metric['key'] }}">
            <dt><x-card-motif :variant="match($metric['key']) { 'wappr_records' => 'records', 'pdm_entries' => 'measurement', 'inspection_recommendations' => 'inspection', default => 'inventory' }" class="card-motif--corner" />{{ $metric['label'] }}</dt>
            <dd class="overview-value">{{ $metric['value'] === null ? '—' : number_format($metric['value'], 0, ',', '.') }}<small>{{ $metric['value'] === null ? 'Belum tersedia' : $metric['unit'] }}</small></dd>
            <dd class="overview-scope">{{ $metric['scope'] }}</dd>
            <dd><a href="{{ route($metric['route']) }}">Lihat sumber <span aria-hidden="true">→</span></a></dd>
        </div>
    @endforeach
</dl>

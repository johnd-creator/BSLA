@php use App\Models\AssetDisruptionWorkOrder; @endphp
<section class="panel detail-panel disruption-detail">
    <div class="detail-heading"><h2>Hubungan WO dengan kejadian</h2>@can('update-asset-disruption', $event)<a class="button secondary" href="{{ route('disruptions.work-orders', $event) }}">Pilih / koreksi hubungan WO</a>@endcan</div>
    <p class="data-note">Identitas WO dicocokkan dengan aset utama saat ditautkan. Hubungan kejadian adalah catatan engineer, bukan validasi failure, downtime, MTBF atau MTTR.</p>
    @forelse($event->workOrders->where('relation_state', '!=', 'removed') as $link)
        <div><h3><a class="text-link" href="{{ route('work-orders.show', ['ref'=>$link->work_order_ref, 'event'=>$link->record_ref, 'asset_ref'=>$link->asset_ref]) }}">WO {{ $link->number() }}</a> · {{ AssetDisruptionWorkOrder::STATES[$link->relation_state] }}</h3><p class="disruption-prose">{{ $link->note ?: 'Dasar hubungan belum dicatat.' }}</p><p class="field-hint">Identitas dicocokkan {{ $link->identity_checked_at->format('d M Y H:i:s') }} UTC; bukan jaminan kondisi sumber saat ini.</p></div>
    @empty<p>Belum ada hubungan WO aktif. Referensi manual tetap belum dicocokkan.</p>@endforelse
</section>

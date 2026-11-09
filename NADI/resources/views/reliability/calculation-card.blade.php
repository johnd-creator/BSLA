@if(isset($report['calculation']))
@php $calculation=$report['calculation']; $effectiveApproval=$approvalStatus ?? $report['approval'] ?? null; @endphp
<section class="panel reliability-panel detail-panel" id="reliability-calculation">
    <h2>Hasil hitung pilot & status resmi</h2>
    <p>Mesin menghitung ulang dari interval dan episode yang dapat ditelusuri. Angka pilot muncul hanya ketika gerbang data/metode lokal terpenuhi. Angka pilot bukan KPI resmi.</p>
    <div class="reliability-readiness-grid">
    @foreach(['mtbf'=>'MTBF pilot', 'mttr'=>'MTTR pilot sesuai definisi', 'active_repair'=>'Pilot perbaikan aktif', 'restoration'=>'Pilot pemulihan fungsi'] as $key=>$label)
        @php $metric=$calculation['pilot'][$key]; @endphp
        <div class="reliability-readiness-card">
            <h3>{{ $label }}</h3>
            <p class="reliability-result">{{ $metric['value'] === null ? 'Belum dapat dihitung' : number_format($metric['value'], 3, ',', '.').' jam' }}</p>
            <p class="data-note">{{ $metric['value'] === null ? 'INSUFFICIENT_DATA' : 'PILOT · BELUM RESMI' }}</p>
            <p>{{ $metric['numerator_seconds'] === null ? 'Pembilang belum tersedia' : number_format($metric['numerator_seconds'], 0, ',', '.').' detik terpilih' }} / {{ $metric['denominator_episodes'] }} episode.</p>
            @if($metric['blockers'])
            <details><summary>{{ count($metric['blockers']) }} gerbang belum terpenuhi</summary><ul>
                @foreach($metric['blockers'] as $blocker)<li>{{ str_replace('_',' ', $blocker) }}</li>@endforeach
            </ul></details>
            <p class="data-note">Total bukti yang terlihat dapat parsial; bukan estimasi KPI. Kosong tidak diubah menjadi nol.</p>
            @endif
        </div>
    @endforeach
    </div>
    <div class="notice reliability-official-boundary"><strong>{{ ($effectiveApproval['status'] ?? '') === 'APPROVED' ? 'KPI resmi: pengesahan Supervisor aktif' : 'KPI resmi: belum disahkan' }}</strong>
    <p>Status keputusan saat pemeriksaan: {{ $effectiveApproval['status'] ?? 'AWAITING_SUPERVISOR' }}. Engineer menyiapkan bukti, aturan dan snapshot. Hanya Supervisor dapat mengesahkan metode serta metrik terpilih pada snapshot yang masih cocok dengan bukti terkini. Perubahan bukti, metode atau engine menarik status resmi sampai pengesahan baru.</p>
    @if(($effectiveApproval['status'] ?? '') === 'APPROVED')<dl class="detail-grid">@foreach(['mtbf'=>'MTBF resmi', 'mttr'=>'MTTR resmi'] as $key=>$label)<div><dt>{{ $label }}</dt><dd>{{ $effectiveApproval['metrics'][$key]['value'] === null ? 'Tidak termasuk pengesahan' : number_format($effectiveApproval['metrics'][$key]['value'],3,',','.').' jam' }}</dd></div>@endforeach</dl>@endif
    <p class="data-note">Scope hanya aset {{ $report['asset_ref'] }}, tahun onset {{ $report['period']['year'] }} WIB, versi metode dan definisi metrik yang tercatat. Tidak berlaku bagi aset anak, aset lain atau tahun lain. MTTR dapat disahkan terpisah dari MTBF.</p></div>
    <p class="data-note">MTBF = jam exposure eligible / failure eligible. MTTR mengikuti pilihan perbaikan aktif atau restoration; keduanya memakai denominator sendiri. Semua hasil memakai aset/tahun/versi aturan yang sama. Nol failure tidak menjadi MTBF nol atau tak hingga.</p>
    <div class="form-actions">
        <a class="button secondary" href="{{ isset($snapshot) ? route('reliability.snapshots.calculation',$snapshot) : route('reliability.calculation',['asset_ref'=>$report['asset_ref'],'year'=>$report['period']['year']]) }}">Telusuri pembilang & penyebut</a>
        <a class="button secondary" href="{{ isset($snapshot) ? route('reliability.snapshots.download',$snapshot) : route('reliability.download',['asset_ref'=>$report['asset_ref'],'year'=>$report['period']['year']]) }}">Unduh evidence & hasil JSON</a>
    </div>
    <p class="data-note">Engine {{ $calculation['engine_version'] }} · aturan {{ $calculation['policy_revision'] ? 'v'.$calculation['policy_revision'] : 'belum dicatat' }} · hash perhitungan {{ $calculation['calculation_hash'] }}</p>
</section>
@endif

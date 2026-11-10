<section class="panel reliability-panel detail-panel" id="supervisor-approval">
<h2>Pengesahan metode & hasil oleh Supervisor</h2>
@foreach(['previous_revision','calculation_hash','metrics','metrics.0','metrics.1','method_attestation','result_attestation','evidence','reason','decision','request_key'] as $field)<x-field-error :name="$field" />@endforeach
<p>Engineer menyiapkan/review evidence dan aturan. Supervisor mengesahkan metode beserta metrik yang dipilih, khusus snapshot ini. Ini tidak mengesahkan pekerjaan WO, anggaran atau aset lain.</p>
<p><strong>Scope: {{ $snapshot->asset_ref }} · periode onset {{ \App\Services\ReliabilityPeriod::fromReport($snapshot->report)->label() }} WIB.</strong> Episode perbaikan/pemulihan memakai seluruh durasi episode periode onset. MTBF memakai exposure eligible pada periode exact tersebut. Tidak ada penggabungan plant atau pengesahan otomatis untuk rentang lain.</p>
<p>Status terkini: <strong>{{ $approvalStatus['status'] }}</strong>. Status ini diperiksa terpisah dari isi snapshot historis yang tidak ditimpa.</p>
@if($approvalStatus['approval'])
<p class="data-note">Keputusan scope terakhir #{{ $approvalStatus['approval']['revision'] }} · Supervisor ID {{ $approvalStatus['approval']['created_by'] }} · {{ $approvalStatus['approval']['created_at'] }} · snapshot #{{ $approvalStatus['approval']['reliability_snapshot_id'] }}.</p>
@endif
@if(!$approvalReady)<p class="notice error">Snapshot belum punya mesin hitung terkini atau basisnya sudah berubah. Engineer perlu merekonsiliasi bukti dan aturan, lalu menyimpan snapshot baru sebelum Supervisor dapat mengesahkan.</p>@endif
@if($approvalTableReady)
<a class="button secondary" href="{{ route('reliability.approvals.download', $snapshot) }}">Unduh paket pengesahan JSON</a>
@can('approve-reliability')
@if($approvalReady)
<form method="POST" action="{{ route('reliability.approvals.store', $snapshot) }}" class="reliability-form stack">
@csrf
<input type="hidden" name="request_key" value="{{ $approvalRequestKey }}"><input type="hidden" name="decision" value="approved"><input type="hidden" name="previous_revision" value="{{ $approvalStatus['approval']['revision'] ?? 0 }}"><input type="hidden" name="calculation_hash" value="{{ $report['calculation']['calculation_hash'] }}">
<h3>Pilih metrik untuk disahkan</h3>
<p>Metode v{{ $report['calculation']['policy_revision'] ?? '—' }} · {{ $report['calculation']['engine_version'] }}. MTTR mengikuti definisi {{ $report['readiness']['policy']['mttr_basis'] ?? $report['calculation']['pilot']['mttr']['basis'] }}. Pilih hanya metrik yang telah diperiksa; MTBF dan MTTR tidak saling mewakili.</p>
@foreach(['mtbf'=>'MTBF', 'mttr'=>'MTTR'] as $key=>$label)
@php $metric=$report['calculation']['pilot'][$key]; @endphp
<label class="checkbox-label"><input type="checkbox" name="metrics[]" value="{{ $key }}" @disabled($metric['value'] === null)> {{ $label }} · {{ $metric['value'] === null ? 'Belum cukup data, tidak bisa disahkan' : number_format($metric['value'],3,',','.').' jam · '.$metric['numerator_seconds'].' detik / '.$metric['denominator_episodes'].' episode' }}</label>
@endforeach
<label>Referensi pemeriksaan Supervisor<textarea name="evidence" required minlength="5" maxlength="4000">{{ old('evidence') }}</textarea></label>
<label>Alasan keputusan<textarea name="reason" required minlength="5" maxlength="2000">{{ old('reason') }}</textarea></label>
<label class="checkbox-label"><input type="checkbox" name="method_attestation" value="1" required> Saya mengesahkan definisi fungsi/failure, scope aset/periode exact, aturan exposure/recurrence/kelengkapan dan definisi MTTR pada versi metode snapshot ini.</label>
<label class="checkbox-label"><input type="checkbox" name="result_attestation" value="1" required> Saya telah memeriksa evidence, pengecualian, pembilang/penyebut dan hasil metrik terpilih. Saya mengesahkannya sebagai hasil resmi untuk scope ini.</label>
<p class="data-note">Keputusan baru menggantikan pengesahan aktif sebelumnya untuk scope aset/periode exact ini. Metrik yang tidak dipilih tidak tetap resmi. Riwayat keputusan tidak dihapus.</p>
<button class="button primary" type="submit">Sahkan metode & metrik terpilih</button>
</form>
@endif
@if(($approvalStatus['approval']['decision'] ?? null) === 'approved' && $approvalStatus['approval']['reliability_snapshot_id'] === $snapshot->id)
<details><summary>Cabut pengesahan snapshot ini</summary>
<form method="POST" action="{{ route('reliability.approvals.store', $snapshot) }}" class="reliability-form stack">@csrf
<input type="hidden" name="request_key" value="{{ $approvalRequestKey }}"><input type="hidden" name="decision" value="revoked"><input type="hidden" name="previous_revision" value="{{ $approvalStatus['approval']['revision'] }}"><input type="hidden" name="calculation_hash" value="{{ $report['calculation']['calculation_hash'] }}">
<label>Referensi pencabutan<textarea name="evidence" required minlength="5" maxlength="4000"></textarea></label><label>Alasan pencabutan<textarea name="reason" required minlength="5" maxlength="2000"></textarea></label><button class="button secondary" type="submit">Cabut pengesahan</button>
</form></details>
@endif
@else
<p class="data-note">Hanya akun dengan role SUPERVISOR dapat mengesahkan atau mencabut. ENGINEER, ADMIN dan MANAGER tanpa role tersebut hanya dapat membaca keputusan.</p>
@endcan
@else
<p class="notice error">Penyimpanan pengesahan belum tersedia. Migrasi diperlukan sebelum keputusan dapat dicatat.</p>
@endif
<h3>Audit keputusan scope aset/periode exact</h3>
@forelse($approvalHistory as $decision)
<details><summary>Revisi {{ $decision->revision }} · {{ $decision->decision }} · snapshot #{{ $decision->reliability_snapshot_id }}</summary>
<p>Supervisor ID {{ $decision->created_by }} · {{ $decision->created_at->toIso8601String() }} · metode v{{ $decision->policy_revision }} · {{ $decision->engine_version }} · metrik {{ implode(', ', $decision->metrics) }}.</p>
<p>{{ $decision->evidence }}</p><p>{{ $decision->reason }}</p>
@foreach($decision->approved_values as $key=>$metric)<p>Nilai historis {{ strtoupper($key) }}: {{ number_format($metric['value'],3,',','.') }} jam. Ini bukan pernyataan status resmi saat ini.</p>@endforeach
<p class="data-note">Hash perhitungan {{ $decision->calculation_hash }}</p>
</details>
@empty<p>Belum ada keputusan Supervisor untuk scope ini.</p>@endforelse
@if($approvalHistory instanceof \Illuminate\Contracts\Pagination\Paginator){{ $approvalHistory->links() }}@endif
</section>

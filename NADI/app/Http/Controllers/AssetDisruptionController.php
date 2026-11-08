<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Services\DisruptionLogbook;
use App\Services\ReliabilityMart;
use Carbon\CarbonImmutable;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class AssetDisruptionController extends Controller
{
    public function index(Request $request, DisruptionLogbook $logbook)
    {
        $filters = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,2200'], 'status' => ['nullable', Rule::in(['recorded', 'voided'])]]);
        $assetRef = $filters['asset_ref'] ?? null;
        $query = AssetDisruption::with(['author:id,name', 'members'])->when($assetRef, fn ($query) => $query->forAsset($assetRef))
            ->where('status', $filters['status'] ?? 'recorded');
        if (! empty($filters['year'])) {
            $query->whereBetween('occurred_on', [$filters['year'].'-01-01', $filters['year'].'-12-31']);
        }

        return view('disruptions.index', ['events' => $query->orderByDesc('occurred_on')->orderByDesc('id')->paginate(20)->withQueryString(), 'assetRef' => $assetRef, 'summary' => $logbook->summary($assetRef)]);
    }

    public function create(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        $filters = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'], 'q' => ['nullable', 'string', 'max:120'], 'offset' => ['nullable', 'integer', 'between:0,1000000']]);
        $asset = $page = null;
        $unavailable = false;
        try {
            if (! empty($filters['asset_ref'])) {
                $asset = $mart->historyAsset($filters['asset_ref']);
            } else {
                $page = $mart->inventory(['q' => $filters['q'] ?? '', 'offset' => (int) ($filters['offset'] ?? 0)]);
            }
        } catch (Throwable) {
            $unavailable = true;
        }
        if ($asset || ($unavailable && $request->old('asset_ref') === ($filters['asset_ref'] ?? null) && $request->old('request_key'))) {
            return view('disruptions.form', ['event' => new AssetDisruption(['asset_ref' => $asset['canonical_id'] ?? $filters['asset_ref']]), 'asset' => $asset, 'requestKey' => (string) Str::uuid(), 'unavailable' => $unavailable]);
        }

        return view('disruptions.choose', compact('page', 'unavailable'));
    }

    private function validated(Request $request, ReliabilityMart $mart, ?AssetDisruption $event = null): array
    {
        $data = $request->validate([
            'asset_ref' => ['required', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'asset_role' => ['required', Rule::in(array_keys(AssetDisruption::ROLES))],
            'affected_refs' => ['nullable', 'string', 'max:5000'],
            'cause_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'event_type' => ['required', Rule::in(array_keys(AssetDisruption::TYPES))],
            'description' => ['nullable', 'string', 'max:4000'],
            'known_cause' => ['nullable', 'string', 'max:4000'],
            'impact' => ['required', Rule::in(array_keys(AssetDisruption::IMPACTS))],
            'impact_note' => ['nullable', 'string', 'max:2000'],
            'occurred_on' => ['nullable', 'required_with:occurred_time', 'date_format:Y-m-d', 'before_or_equal:today'],
            'occurred_time' => ['nullable', 'date_format:H:i,H:i:s'],
            'restored_on' => ['nullable', 'required_with:restored_time', 'date_format:Y-m-d', 'before_or_equal:today'],
            'restored_time' => ['nullable', 'date_format:H:i,H:i:s'],
            'timezone' => ['nullable', 'required_with:occurred_time,restored_time', Rule::in(array_keys(AssetDisruption::ZONES))],
            'work_order_ref' => ['nullable', 'string', 'max:200'],
            'evidence_note' => ['nullable', 'string', 'max:4000'],
            'status' => [$event ? 'required' : 'nullable', Rule::in(['recorded', 'voided'])],
            'version' => [$event ? 'required' : 'nullable', 'integer', 'min:1'],
            'correction_reason' => [$event ? 'required' : 'nullable', 'string', 'min:5', 'max:2000'],
        ]);
        if ($event && $event->asset_ref !== $data['asset_ref']) {
            throw ValidationException::withMessages(['asset_ref' => 'Aset utama tidak dapat diganti. Batalkan catatan keliru dengan alasan, lalu buat catatan baru.']);
        }
        $members = [['asset_ref' => $data['asset_ref'], 'role' => $data['asset_role']]];
        $affected = preg_split('/[\r\n,]+/', $data['affected_refs'] ?? '', -1, PREG_SPLIT_NO_EMPTY);
        $affected = array_values(array_filter(array_map('trim', $affected)));
        if (count($affected) > 20 || count($affected) !== count(array_unique($affected))) {
            throw ValidationException::withMessages(['affected_refs' => 'Maksimal 20 aset terdampak, masing-masing hanya sekali.']);
        }
        foreach ($affected as $ref) {
            if (strlen($ref) > 240 || str_contains($ref, '/') || str_contains($ref, '\\') || $ref === $data['asset_ref']) {
                throw ValidationException::withMessages(['affected_refs' => 'Gunakan Canonical ID aset lain yang valid, tanpa duplikasi aset utama.']);
            }
            $members[] = ['asset_ref' => $ref, 'role' => 'affected'];
        }
        if (! empty($data['cause_ref'])) {
            if ($data['asset_role'] === 'cause' || in_array($data['cause_ref'], array_column($members, 'asset_ref'), true)) {
                throw ValidationException::withMessages(['cause_ref' => 'Satu kejadian hanya memiliki satu aset penyebab yang dicatat; identitas tidak boleh berulang.']);
            }
            $members[] = ['asset_ref' => $data['cause_ref'], 'role' => 'cause'];
        }
        foreach ($members as $member) {
            try {
                $mart->historyAsset($member['asset_ref']);
            } catch (Throwable) {
                $field = $member['asset_ref'] === $data['asset_ref'] ? 'asset_ref' : ($member['role'] === 'cause' ? 'cause_ref' : 'affected_refs');
                throw ValidationException::withMessages([$field => 'Identitas aset belum dapat diverifikasi melalui inventori/Mart. Isian dipertahankan; periksa ID atau coba lagi setelah koneksi pulih.']);
            }
        }
        $times = [];
        $zone = null;
        foreach (['occurred', 'restored'] as $field) {
            $times[$field.'_on'] = $data[$field.'_on'] ?? null;
            $times[$field.'_at'] = null;
            if (! empty($data[$field.'_time'])) {
                $zone = $data['timezone'];
                $time = $data[$field.'_time'];
                $format = strlen($time) === 8 ? '!Y-m-d H:i:s' : '!Y-m-d H:i';
                $instant = CarbonImmutable::createFromFormat($format, $data[$field.'_on'].' '.$time, $zone)->utc();
                if ($instant->isFuture()) {
                    throw ValidationException::withMessages([$field.'_time' => 'Waktu tidak boleh di masa depan. Periksa zona waktu.']);
                }
                $times[$field.'_at'] = $instant;
            }
        }
        if (($times['occurred_on'] && $times['restored_on'] && $times['restored_on'] < $times['occurred_on']) ||
            ($times['occurred_at'] && $times['restored_at'] && $times['restored_at']->lt($times['occurred_at']))) {
            throw ValidationException::withMessages(['restored_on' => 'Waktu kembali siap tidak boleh sebelum kejadian.']);
        }

        return ['values' => [...array_intersect_key($data, array_flip(['asset_ref', 'event_type', 'description', 'known_cause', 'impact', 'impact_note', 'work_order_ref', 'evidence_note'])), 'description' => $data['description'] ?? '', ...$times, 'timezone' => $zone, 'status' => $event ? $data['status'] : 'recorded'], 'members' => $members];
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        $existing = AssetDisruption::where('request_key', $key)->first();
        if ($existing) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('disruptions.show', $existing)->with('status', 'Form ini sudah tersimpan sebagai satu kejadian.');
        }
        $data = $this->validated($request, $mart);
        $event = DB::transaction(function () use ($request, $data, $key) {
            $event = AssetDisruption::firstOrCreate(['request_key' => $key], [...$data['values'], 'created_by' => $request->user()->id]);
            abort_unless($event->created_by === $request->user()->id, 409);
            if ($event->wasRecentlyCreated) {
                $event->members()->createMany($data['members']);
                $this->revision($event->fresh(), $request->user()->id, 'Catatan awal');
            }

            return $event;
        });

        return redirect()->route('disruptions.show', $event)->with('status', 'Log gangguan tersimpan. Ini catatan engineer, bukan diagnosis atau skor resmi.');
    }

    public function show(AssetDisruption $disruption)
    {
        $input = request()->validate(['revision' => ['nullable', 'integer', 'min:1'], 'page' => ['nullable', 'integer', 'between:1,1000']]);

        return view('disruptions.show', ['event' => $disruption->load(['author:id,name', 'members', 'workOrders']),
            'revisions' => $disruption->revisions()->with('author:id,name')->when(! empty($input['revision']), fn ($q) => $q->where('version', $input['revision']))->paginate(10)->withQueryString()]);
    }

    public function edit(AssetDisruption $disruption)
    {
        Gate::authorize('update-asset-disruption', $disruption);

        return view('disruptions.form', ['event' => $disruption->load('members'), 'asset' => null, 'requestKey' => null]);
    }

    public function update(Request $request, AssetDisruption $disruption, ReliabilityMart $mart)
    {
        Gate::authorize('update-asset-disruption', $disruption);
        $data = $this->validated($request, $mart, $disruption);
        DB::transaction(function () use ($request, $data, $disruption) {
            $updated = AssetDisruption::whereKey($disruption->id)->where('version', $request->integer('version'))
                ->update([...$data['values'], 'version' => DB::raw('version + 1')]);
            if (! $updated) {
                throw ValidationException::withMessages(['version' => 'Catatan sudah berubah. Buka ulang form sebelum menyimpan agar koreksi sebelumnya tidak tertimpa.']);
            }
            // Replacement affects current membership only; every prior version remains in the audit snapshots.
            $disruption->members()->delete();
            $disruption->members()->createMany($data['members']);
            $this->revision($disruption->fresh(), $request->user()->id, $request->string('correction_reason')->toString());
        });

        return redirect()->route('disruptions.show', $disruption)->with('status', 'Koreksi tersimpan beserta versi sebelumnya dan alasan perubahan.');
    }

    private function revision(AssetDisruption $event, int $author, string $reason): void
    {
        $event->revisions()->create(['version' => $event->version, 'changed_by' => $author, 'reason' => $reason, 'snapshot' => $event->snapshot(), 'created_at' => now()]);
    }
}

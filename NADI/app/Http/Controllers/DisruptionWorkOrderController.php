<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Models\AssetDisruptionWorkOrder;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class DisruptionWorkOrderController extends Controller
{
    private const PREFIX = 'workorder:MAXIMO:MXWODETAIL:BSR:IP:';

    public function index(Request $request, AssetDisruption $disruption, ReliabilityMart $mart)
    {
        Gate::authorize('update-asset-disruption', $disruption);
        $filters = $request->validate(['wo_number' => ['nullable', 'string', 'max:100', 'not_regex:/[\x00-\x1F\x7F]/'], 'offset' => ['nullable', 'integer', 'between:0,1000000']]);
        $page = null;
        try {
            $asset = $mart->historyAsset($disruption->asset_ref);
            $page = $mart->workOrders(array_filter(['asset_ref' => $disruption->asset_ref, 'offset' => (int) ($filters['offset'] ?? 0), 'work_order_id' => empty($filters['wo_number']) ? null : self::PREFIX.rawurlencode($filters['wo_number'])], fn ($value) => $value !== null), ! $asset['registered']);
            // Fail closed if a candidate cannot be safely selected by its exact identity.
            foreach ($page['items'] as $record) {
                if (! $this->validIdentity($record, $disruption->asset_ref) || (! empty($filters['wo_number']) && $record['work_order_id'] !== self::PREFIX.rawurlencode($filters['wo_number']))) {
                    throw new \RuntimeException('Invalid work order candidate.');
                }
            }
        } catch (Throwable) {
            $page = null;
        }

        return view('disruptions.work-orders', ['event' => $disruption->load('workOrders'), 'page' => $page]);
    }

    public function store(Request $request, AssetDisruption $disruption, ReliabilityMart $mart)
    {
        Gate::authorize('update-asset-disruption', $disruption);
        $data = $request->validate([
            'version' => ['required', 'integer', 'min:1'],
            'work_order_ref' => ['required', 'string', 'max:200', 'starts_with:'.self::PREFIX, 'not_regex:/[\\\\\/]/'],
            'note' => ['nullable', 'string', 'max:2000'],
        ]);
        $existing = $disruption->workOrders()->where('work_order_ref', $data['work_order_ref'])->first();
        if ($existing && $existing->relation_state !== 'removed') {
            return redirect()->route('disruptions.work-orders', $disruption)->with('status', 'WO ini sudah ditautkan sekali. Gunakan koreksi hubungan untuk mengubah catatannya.');
        }
        $this->assertCurrent($disruption, $data['version']);
        try {
            $asset = $mart->historyAsset($disruption->asset_ref);
            $record = $mart->workOrder($data['work_order_ref'], null, $disruption->asset_ref, ! $asset['registered']);
            if (! $this->validIdentity($record, $disruption->asset_ref)) {
                throw new \RuntimeException('Invalid work order identity.');
            }
        } catch (Throwable) {
            throw ValidationException::withMessages(['work_order_ref' => 'WO belum dapat diverifikasi cocok persis dengan aset utama. Isian dipertahankan; periksa pilihan atau coba setelah koneksi pulih.']);
        }
        DB::transaction(function () use ($request, $disruption, $data, $record) {
            $this->advance($disruption, $data['version']);
            if ($disruption->workOrders()->where('relation_state', '!=', 'removed')->count() >= 20) {
                throw ValidationException::withMessages(['work_order_ref' => 'Maksimal 20 WO aktif per kejadian.']);
            }
            $disruption->workOrders()->updateOrCreate(['work_order_ref' => $data['work_order_ref']], [
                'asset_ref' => $disruption->asset_ref, 'record_ref' => $record['canonical_id'], 'relation_state' => 'uncertain',
                'note' => $data['note'] ?? null, 'identity_checked_at' => now(),
            ]);
            $this->revision($disruption, $request->user()->id, 'Menautkan WO; hubungan belum dipastikan');
        });

        return redirect()->route('disruptions.work-orders', $disruption)->with('status', 'Identitas WO cocok dengan aset. Hubungan dengan kejadian tetap belum dipastikan.');
    }

    public function update(Request $request, AssetDisruption $disruption, AssetDisruptionWorkOrder $link)
    {
        Gate::authorize('update-asset-disruption', $disruption);
        abort_unless($link->asset_disruption_id === $disruption->id, 404);
        $data = $request->validate([
            'version' => ['required', 'integer', 'min:1'],
            'relation_state' => ['required', Rule::in(array_keys(AssetDisruptionWorkOrder::STATES))],
            'note' => ['nullable', 'string', 'max:2000'],
            'correction_reason' => ['required', 'string', 'min:5', 'max:2000'],
        ]);
        // A removed identity must be freshly checked through the picker before reuse.
        abort_if($link->relation_state === 'removed', 409);
        DB::transaction(function () use ($request, $disruption, $link, $data) {
            $this->advance($disruption, $data['version']);
            $link->update(['relation_state' => $data['relation_state'], 'note' => $data['note'] ?? null]);
            $this->revision($disruption, $request->user()->id, $data['correction_reason']);
        });

        return redirect()->route('disruptions.work-orders', $disruption)->with('status', 'Koreksi hubungan tersimpan bersama versi sebelumnya. Ini bukan validasi failure.');
    }

    private function validIdentity(array $record, string $asset): bool
    {
        return ($record['equipment_id'] ?? null) === $asset
            && is_string($record['work_order_id'] ?? null) && str_starts_with($record['work_order_id'], self::PREFIX)
            && strlen($record['work_order_id']) > strlen(self::PREFIX) && strlen($record['work_order_id']) <= 200
            && ! preg_match('~[/\\\\]~', $record['work_order_id'])
            && is_string($record['canonical_id'] ?? null) && strlen($record['canonical_id']) <= 200
            && $record['canonical_id'] === 'maintenance_event:'.substr($record['work_order_id'], strlen('workorder:'));
    }

    private function assertCurrent(AssetDisruption $event, int $version): void
    {
        if ($event->version !== $version) {
            throw ValidationException::withMessages(['version' => 'Catatan sudah berubah. Buka ulang halaman agar koreksi sebelumnya tidak tertimpa.']);
        }
    }

    private function advance(AssetDisruption $event, int $version): void
    {
        if (! AssetDisruption::whereKey($event->id)->where('version', $version)->update(['version' => DB::raw('version + 1'), 'updated_at' => now()])) {
            throw ValidationException::withMessages(['version' => 'Catatan sudah berubah. Buka ulang halaman agar koreksi sebelumnya tidak tertimpa.']);
        }
    }

    private function revision(AssetDisruption $event, int $actor, string $reason): void
    {
        $event = $event->fresh();
        $event->revisions()->create(['version' => $event->version, 'changed_by' => $actor, 'reason' => $reason, 'snapshot' => $event->snapshot(), 'created_at' => now()]);
    }
}

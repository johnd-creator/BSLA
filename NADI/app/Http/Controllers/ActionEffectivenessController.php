<?php

namespace App\Http\Controllers;

use App\Models\ActionEffectivenessReview;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Services\ActionEffectiveness;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

class ActionEffectivenessController extends Controller
{
    public function show(Request $request, InspectionDraft $inspection, ActionEffectiveness $evidence)
    {
        abort_unless(trim((string) $inspection->recommendation) !== '', 404);
        $selection = $request->validate(['before_id' => ['nullable', 'integer', 'min:1'], 'after_id' => ['nullable', 'integer', 'min:1']]);
        $latest = ActionEffectivenessReview::where('inspection_draft_id', $inspection->id)->with(['beforeMeasurement', 'afterMeasurement'])->latest('revision')->first();
        $before = $this->measurement(array_key_exists('before_id', $selection) ? $selection['before_id'] : ($latest?->before_activity_id ?? $inspection->pdm_activity_id), $inspection);
        $after = $this->measurement(array_key_exists('after_id', $selection) ? $selection['after_id'] : $latest?->after_activity_id, $inspection);
        $history = ActionEffectivenessReview::where('inspection_draft_id', $inspection->id)->with('author:id,name')->latest('revision')->paginate(10)->withQueryString();
        $candidates = $inspection->asset_ref ? PdmActivity::where('asset_ref', $inspection->asset_ref)->newestMeasurement()->limit(50)->get() : collect();

        return view('action-effectiveness.show', compact('inspection', 'latest', 'before', 'after', 'history', 'candidates', 'evidence'));
    }

    private function measurement(?int $id, InspectionDraft $inspection): ?PdmActivity
    {
        if (! $id) {
            return null;
        }
        $activity = PdmActivity::findOrFail($id);
        abort_unless($inspection->asset_ref && $activity->asset_ref === $inspection->asset_ref, 422, 'Pengukuran harus berasal dari aset rekomendasi ini.');

        return $activity;
    }

    public function store(Request $request, InspectionDraft $inspection, ActionEffectiveness $evidence)
    {
        Gate::authorize('update-inspection-draft', $inspection);
        abort_unless(trim((string) $inspection->recommendation) !== '', 422);
        $data = $request->validate([
            'request_key' => ['required', 'uuid'], 'inspection_version' => ['required', 'integer', 'min:1'],
            'latest_review_id' => ['required', 'integer', 'min:0'],
            'before_id' => ['nullable', 'integer', 'min:1'], 'after_id' => ['nullable', 'integer', 'min:1'],
            'before_version' => ['nullable', 'required_with:before_id', 'integer', 'min:1'],
            'after_version' => ['nullable', 'required_with:after_id', 'integer', 'min:1'],
            'action_taken' => ['required', 'string', 'max:4000'],
            'completed_on' => ['required', 'date_format:Y-m-d', 'before_or_equal:'.now('Asia/Jakarta')->toDateString()],
            'point' => ['nullable', 'string', 'max:120'],
            'decision' => ['required', Rule::in(array_keys(ActionEffectivenessReview::DECISIONS))],
            'reason' => ['required', 'string', 'max:4000'], 'acknowledge_review' => ['required', 'accepted'],
        ]);
        DB::transaction(function () use ($data, $inspection, $request, $evidence) {
            // Match the measurement -> inspection lock order used by existing analysis edits.
            $ids = array_values(array_filter([$data['before_id'] ?? null, $data['after_id'] ?? null]));
            $measurements = PdmActivity::whereIn('id', $ids)->orderBy('id')->lockForUpdate()->get()->keyBy('id');
            $current = InspectionDraft::whereKey($inspection->id)->lockForUpdate()->firstOrFail();
            Gate::authorize('update-inspection-draft', $current);
            if ($existing = ActionEffectivenessReview::where('request_key', $data['request_key'])->first()) {
                abort_unless($existing->inspection_draft_id === $current->id && $existing->created_by === $request->user()->id, 409);

                return;
            }
            $latest = ActionEffectivenessReview::where('inspection_draft_id', $current->id)->latest('revision')->first();
            if ($current->version !== (int) $data['inspection_version'] || ($latest?->id ?? 0) !== (int) $data['latest_review_id']) {
                throw ValidationException::withMessages(['inspection_version' => 'Rekomendasi atau review sudah berubah. Muat ulang sebelum menilai.']);
            }
            abort_unless(trim((string) $current->recommendation) !== '', 422);
            $selected = [];
            foreach (['before', 'after'] as $key) {
                $activity = ! empty($data[$key.'_id']) ? $measurements->get($data[$key.'_id']) : null;
                if (! empty($data[$key.'_id']) && (! $activity || $activity->asset_ref !== $current->asset_ref || $activity->version !== (int) $data[$key.'_version'])) {
                    throw ValidationException::withMessages([$key.'_id' => 'Pengukuran tidak cocok atau sudah berubah. Pilih ulang bukti dari aset ini.']);
                }
                $selected[$key] = $activity;
            }
            $comparison = $evidence->comparison($current, $selected['before'], $selected['after'], $data['point'] ?? null, $data['completed_on']);
            $evidence->validateDecision($comparison, $data['decision']);
            ActionEffectivenessReview::create([
                'inspection_draft_id' => $current->id, 'revision' => ($latest?->revision ?? 0) + 1,
                'created_by' => $request->user()->id, 'request_key' => $data['request_key'],
                'before_activity_id' => $selected['before']?->id, 'after_activity_id' => $selected['after']?->id,
                'action_taken' => $data['action_taken'], 'completed_on' => $data['completed_on'],
                'point' => $data['point'] ?? null, 'decision' => $data['decision'], 'reason' => $data['reason'],
                'evidence' => ['inspection' => $evidence->inspectionBasis($current),
                    'before' => $selected['before'] ? $evidence->snapshot($selected['before']) : null,
                    'after' => $selected['after'] ? $evidence->snapshot($selected['after']) : null,
                    'comparison' => $comparison], 'created_at' => now(),
            ]);
        });

        return redirect()->route('inspections.effectiveness', $inspection)->with('status', 'Review efektivitas tersimpan dengan bukti saat ditinjau. Status tindak lanjut tidak diubah otomatis.');
    }
}

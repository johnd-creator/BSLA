<?php

namespace App\Services;

use App\Models\InspectionDraft;
use App\Models\WorkspaceActivity;
use Illuminate\Database\Eloquent\Model;

class WorkspaceActivityLog
{
    public static function history(string $kind, int $subject)
    {
        $input = request()->validate(['activity_id' => ['nullable', 'integer', 'min:1'], 'audit_page' => ['nullable', 'integer', 'between:1,1000']]);

        return WorkspaceActivity::query()->with('actor:id,name')->where('kind', $kind)->where('subject_id', $subject)
            ->when(! empty($input['activity_id']), fn ($query) => $query->whereKey($input['activity_id']))
            ->orderByDesc('id')->simplePaginate(10, ['*'], 'audit_page')->withQueryString();
    }

    /** Called only by authorized writes, inside the same transaction as the draft. */
    public static function record(Model $draft, int $actor, array $before = []): void
    {
        $kind = $draft instanceof InspectionDraft ? 'inspection' : 'pdm';
        $changes = [];
        foreach ($before as $field => $value) {
            if ($draft->getRawOriginal($field) !== $value) {
                $changes[$field] = ['before' => $value, 'after' => $draft->getRawOriginal($field)];
            }
        }
        if ($draft->wasRecentlyCreated && $kind === 'inspection' && $draft->recommendation) {
            $changes['recommendation'] = ['before' => null, 'after' => $draft->recommendation];
        }
        // Initial creation is recorded explicitly. No historical backfill from updated_at.
        WorkspaceActivity::create([
            'kind' => $kind, 'subject_id' => $draft->id, 'version' => $draft->version,
            'actor_id' => $actor, 'asset_ref' => $draft->asset_ref,
            'action' => $draft->wasRecentlyCreated ? 'created' : 'updated',
            'changes' => $changes, 'created_at' => now(),
        ]);
    }
}

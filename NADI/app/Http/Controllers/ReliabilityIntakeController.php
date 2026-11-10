<?php

namespace App\Http\Controllers;

use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityIntake;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\ValidationException;

class ReliabilityIntakeController extends Controller
{
    private function scope(Request $request, bool $required = false): array
    {
        $data = $request->validate(['asset_ref' => [$required ? 'required' : 'nullable', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'intake_page' => ['nullable', 'integer', 'between:1,1000']]);

        return [$data['asset_ref'] ?? null, ReliabilityPeriod::fromRequest($request)];
    }

    public function index(Request $request)
    {
        return $this->page($request);
    }

    public function preview(Request $request, ReliabilityIntake $intake)
    {
        Gate::authorize('write-asset-disruptions');
        [$asset, $period] = $this->scope($request, true);
        $data = $request->validate(['csv_text' => ['required', 'string', 'max:65536']]);
        $rows = $intake->preview($data['csv_text'], $asset, $period);

        return $this->page($request, $rows);
    }

    private function page(Request $request, ?array $preview = null)
    {
        [$asset, $period] = $this->scope($request);
        $report = $asset ? app(ReliabilityEvidence::class)->report($asset, $period, app(ReliabilityMart::class)) : null;
        $rows = collect($report['events'] ?? [])->sortBy(fn ($row) => $row['date'] === null ? 0 : ($row['in_year'] ? 1 : 2))->values();
        $events = new LengthAwarePaginator($rows->forPage((int) $request->input('intake_page', 1), 20)->values(), $rows->count(), 20, (int) $request->input('intake_page', 1), ['path' => route('reliability.intake'), 'pageName' => 'intake_page', 'query' => ['asset_ref' => $asset, ...$period->query()], 'fragment' => 'intake-events']);

        return response()->view('reliability.intake', ['assetRef' => $asset, 'period' => $period, 'year' => $period->start->year, 'report' => $report, 'events' => $events, 'preview' => $preview])->header('Cache-Control', 'no-store, private');
    }

    public function draft(Request $request, ReliabilityIntake $intake)
    {
        Gate::authorize('write-asset-disruptions');
        [$asset, $period] = $this->scope($request, true);
        $data = $request->validate(['draft' => ['required', 'array:'.implode(',', ReliabilityIntake::COLUMNS)]]);
        $row = $intake->inspect($data['draft'], $asset, $period);
        if ($row['errors']) {
            throw ValidationException::withMessages(['draft' => $row['errors']]);
        }
        // PRG keeps validation errors on the existing GET review route rather
        // than redirecting the browser to a POST-only draft URL.
        $draft = $row['values'];
        $draft['classification'] = 'uncertain';
        $draft['duplicate_of'] = null;

        return redirect()->route('reliability.reviews', [$row['event'], 'asset_ref' => $asset, ...$period->query()])
            ->with('reliability_intake_draft', ['event_id' => $row['event']->id, 'asset_ref' => $asset, 'values' => $draft, 'warnings' => $row['warnings'], 'period' => $period->metadata()]);
    }

    public function template()
    {
        Gate::authorize('write-asset-disruptions');

        return response(implode(',', ReliabilityIntake::COLUMNS)."\n", 200, ['Content-Type' => 'text/csv; charset=UTF-8', 'Content-Disposition' => 'attachment; filename="nadi-intake-template.csv"', 'Cache-Control' => 'no-store, private', 'X-Content-Type-Options' => 'nosniff']);
    }
}

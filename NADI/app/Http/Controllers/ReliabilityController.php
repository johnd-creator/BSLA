<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Models\ReliabilityApproval;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Services\ReliabilityApprovalStatus;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use App\Services\ReliabilityReviewQueue;
use App\Services\ReviewedFailureTrends;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class ReliabilityController extends Controller
{
    private function filters(Request $request): array
    {
        return $request->validate(['asset_ref' => ['nullable', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year]]);
    }

    public function index(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart, ReliabilityReviewQueue $queue)
    {
        $filters = $this->filters($request);
        $queueFilters = $this->queueFilters($request);
        $trendFilters = $this->trendFilters($request);
        $asset = $filters['asset_ref'] ?? null;
        $period = ReliabilityPeriod::fromRequest($request);
        $year = $period->start->year;

        $report = $asset ? $evidence->report($asset, $period, $mart) : null;

        return view('reliability.index', ['assetRef' => $asset, 'year' => $year, 'period' => $period, 'report' => $report,
            'trendFilters' => $trendFilters, 'trendView' => $report ? app(ReviewedFailureTrends::class)->select($report['trends'], $trendFilters['trend_basis'], $trendFilters['trend_month'], $trendFilters['trend_period_month']) : null,
            'queueFilters' => $queueFilters, 'reviewQueue' => $report ? $queue->paginate($report, $queueFilters, $request->url(), ['asset_ref' => $asset, ...$period->query()]) : null,
            'snapshots' => $asset ? ReliabilitySnapshot::where('asset_ref', $asset)->where('report->period->start_inclusive', $period->start->toIso8601String())->where('report->period->end_exclusive', $period->end->toIso8601String())->when($period->annual, fn ($q) => $q->whereNull('report->period->kind'), fn ($q) => $q->where('report->period->kind', 'range'))->latest('id')->paginate(10) : null,
            'localAssets' => AssetDisruption::query()->select('asset_ref')->distinct()->limit(100)->pluck('asset_ref'), 'requestKey' => (string) Str::uuid()]);
    }

    public function download(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $filters = $this->filters($request);
        abort_unless(! empty($filters['asset_ref']), 422);
        $report = $evidence->report($filters['asset_ref'], ReliabilityPeriod::fromRequest($request), $mart);

        return $this->jsonDownload($report, 'nadi-reliability-'.ReliabilityPeriod::fromReport($report)->start->toDateString().'-'.ReliabilityPeriod::fromReport($report)->end->subDay()->toDateString().'.json');
    }

    public function store(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        $data = $request->validate(['request_key' => ['required', 'uuid']]);
        $filters = $this->filters($request);
        abort_unless(! empty($filters['asset_ref']), 422);
        $period = ReliabilityPeriod::fromRequest($request);
        $year = $period->start->year;
        if ($existing = ReliabilitySnapshot::where('request_key', $data['request_key'])->first()) {
            abort_unless($existing->created_by === $request->user()->id && $existing->asset_ref === $filters['asset_ref'] && ReliabilityPeriod::fromReport($existing->report)->query() === $period->query(), 409);

            return redirect()->route('reliability.snapshots.show', $existing);
        }
        $report = $evidence->report($filters['asset_ref'], $period, $mart);
        abort_unless($report['asset'] !== null || $report['quality']['all_local_observations'] > 0, 422);
        $snapshot = ReliabilitySnapshot::create(['created_by' => $request->user()->id, 'request_key' => $data['request_key'], 'asset_ref' => $filters['asset_ref'], 'year' => $report['period']['year'], 'rule_version' => ReliabilityReview::RULE, 'evidence_hash' => $report['evidence_hash'], 'report' => $report, 'created_at' => now()]);

        return redirect()->route('reliability.snapshots.show', $snapshot)->with('status', 'Snapshot immutable tersimpan. Koreksi berikutnya tidak menimpa hasil ini.');
    }

    public function show(Request $request, ReliabilitySnapshot $snapshot, ReliabilityEvidence $evidence, ReliabilityMart $mart, ReliabilityReviewQueue $queue)
    {
        $queueFilters = $this->queueFilters($request);
        $trendFilters = $this->trendFilters($request);
        $current = $evidence->report($snapshot->asset_ref, ReliabilityPeriod::fromReport($snapshot->report), $mart);

        return view('reliability.snapshot', ['approvalStatus' => app(ReliabilityApprovalStatus::class)->current($current, $snapshot),
            'approvalReady' => ReliabilityPeriod::fromReport($snapshot->report)->storageReady('reliability_approvals') && isset($snapshot->report['calculation']) && hash_equals($snapshot->report['calculation']['calculation_hash'], $current['calculation']['calculation_hash']),
            'approvalHistory' => ReliabilityPeriod::fromReport($snapshot->report)->storageReady('reliability_approvals') ? ReliabilityPeriod::fromReport($snapshot->report)->constrain(ReliabilityApproval::where('asset_ref', $snapshot->asset_ref))->latest('revision')->paginate(10, ['*'], 'approval_page')->withQueryString() : collect(),
            'approvalRequestKey' => (string) Str::uuid(), 'approvalTableReady' => ReliabilityPeriod::fromReport($snapshot->report)->storageReady('reliability_approvals'), 'snapshot' => $snapshot, 'report' => $snapshot->report, 'changed' => ! hash_equals($snapshot->evidence_hash, $current['evidence_hash']),
            'trendFilters' => $trendFilters, 'trendView' => isset($snapshot->report['trends']['points']) ? app(ReviewedFailureTrends::class)->select($snapshot->report['trends'], $trendFilters['trend_basis'], $trendFilters['trend_month'], $trendFilters['trend_period_month']) : null,
            'queueFilters' => $queueFilters, 'reviewQueue' => $queue->paginate($snapshot->report, $queueFilters, $request->url())]);
    }

    public function snapshotDownload(ReliabilitySnapshot $snapshot)
    {
        return $this->jsonDownload($snapshot->report, 'nadi-reliability-snapshot-'.$snapshot->id.'.json');
    }

    public function calculation(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $this->traceFilters($request);
        $filters = $this->filters($request);
        abort_unless(! empty($filters['asset_ref']), 422);
        $report = $evidence->report($filters['asset_ref'], ReliabilityPeriod::fromRequest($request), $mart);

        return $this->calculationView($request, $report);
    }

    public function snapshotCalculation(Request $request, ReliabilitySnapshot $snapshot, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $this->traceFilters($request);
        $current = $evidence->report($snapshot->asset_ref, ReliabilityPeriod::fromReport($snapshot->report), $mart);

        return $this->calculationView($request, $snapshot->report, $snapshot, app(ReliabilityApprovalStatus::class)->current($current, $snapshot));
    }

    private function calculationView(Request $request, array $report, ?ReliabilitySnapshot $snapshot = null, ?array $approvalStatus = null)
    {
        $filters = $this->traceFilters($request);
        $rows = collect($report['calculation']['event_trace'] ?? []);
        if (! empty($filters['trace_month'])) {
            $rows = $rows->where('month', (int) $filters['trace_month']);
        }
        if (! empty($filters['trace_period_month'])) {
            $rows = $rows->where('period_month', $filters['trace_period_month']);
        }
        $metric = $filters['trace_metric'] ?? 'all';
        $rows = $rows->filter(fn ($row) => match ($metric) {
            'count' => $row['eligible_failure'], 'active_repair', 'restoration' => $row[$metric.'_seconds'] !== null,
            'excluded' => ! $row['eligible_failure'], default => true,
        })->values();
        $page = (int) ($filters['trace_page'] ?? 1);
        $traceRows = new LengthAwarePaginator($rows->forPage($page, 20)->values(), $rows->count(), 20, $page, ['path' => $request->url(), 'pageName' => 'trace_page']);
        $traceRows->appends([...$request->except('trace_page'), ...($snapshot ? [] : ReliabilityPeriod::fromReport($report)->query())]);

        $exposure = collect($report['calculation']['exposure_trace'] ?? []);
        $exposurePage = (int) ($filters['exposure_page'] ?? 1);
        $exposureRows = new LengthAwarePaginator($exposure->forPage($exposurePage, 20)->values(), $exposure->count(), 20, $exposurePage, ['path' => $request->url(), 'pageName' => 'exposure_page']);
        $exposureRows->appends([...$request->except('exposure_page'), ...($snapshot ? [] : ReliabilityPeriod::fromReport($report)->query())]);

        return view('reliability.calculation', compact('report', 'snapshot', 'filters', 'traceRows', 'exposureRows', 'approvalStatus'));
    }

    private function traceFilters(Request $request): array
    {
        return $request->validate(['exposure_page' => ['nullable', 'integer', 'between:1,1000'], 'trace_page' => ['nullable', 'integer', 'between:1,1000'], 'trace_month' => ['nullable', 'integer', 'between:1,12'],
            'trace_period_month' => ['nullable', 'date_format:Y-m'],
            'trace_metric' => ['nullable', Rule::in(['all', 'count', 'active_repair', 'restoration', 'excluded'])]]);
    }

    private function trendFilters(Request $request): array
    {
        $data = $request->validate(['trend_basis' => ['nullable', Rule::in(array_keys(ReviewedFailureTrends::BASES))], 'trend_month' => ['nullable', 'integer', 'between:1,12'], 'trend_period_month' => ['nullable', 'date_format:Y-m']]);

        return ['trend_period_month' => $data['trend_period_month'] ?? null, 'trend_basis' => $data['trend_basis'] ?? 'count', 'trend_month' => isset($data['trend_month']) ? (int) $data['trend_month'] : null];
    }

    private function queueFilters(Request $request): array
    {
        return $request->validate([
            'review_state' => ['nullable', Rule::in(array_keys(ReliabilityReviewQueue::STATES))],
            'review_period' => ['nullable', Rule::in(array_keys(ReliabilityReviewQueue::PERIODS))],
            'review_page' => ['nullable', 'integer', 'between:1,1000'],
        ]);
    }

    private function jsonDownload(array $report, string $name)
    {
        return response(json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR), 200, ['Content-Type' => 'application/json; charset=UTF-8', 'Content-Disposition' => 'attachment; filename="'.$name.'"', 'Cache-Control' => 'no-store, private', 'X-Content-Type-Options' => 'nosniff']);
    }
}

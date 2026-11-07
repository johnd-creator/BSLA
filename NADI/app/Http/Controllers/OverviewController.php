<?php

namespace App\Http\Controllers;

use App\Services\DataOverview;
use App\Services\HomeFeed;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class OverviewController extends Controller
{
    public function index(Request $request, DataOverview $overview, ReliabilityMart $mart, HomeFeed $feed)
    {
        $filters = $request->validate([
            'activity_type' => ['nullable', Rule::in(array_keys(HomeFeed::TYPES))],
            'scope' => ['nullable', Rule::in(['all', 'local', 'registry'])],
            'freshness' => ['nullable', Rule::in(['all', 'recorded', 'unknown'])],
            'period' => ['nullable', Rule::in(['all', '7', '30', '90'])],
            'activity_page' => ['nullable', 'integer', 'between:1,100'],
        ]);

        return view('home', ['snapshot' => $overview->snapshot($mart), 'feed' => $feed->snapshot($mart, $filters), 'filters' => $filters]);
    }

    public function quality(DataOverview $overview, ReliabilityMart $mart)
    {
        return view('overview.quality', ['snapshot' => $overview->snapshot($mart)]);
    }

    public function reports(DataOverview $overview, ReliabilityMart $mart)
    {
        return view('overview.reports', ['snapshot' => $overview->snapshot($mart)]);
    }

    public function download(DataOverview $overview, ReliabilityMart $mart)
    {
        $snapshot = $overview->snapshot($mart);
        $rows = $overview->reportRows($snapshot);

        return response()->streamDownload(function () use ($rows): void {
            $file = fopen('php://output', 'w');
            fwrite($file, "\xEF\xBB\xBF");
            fputcsv($file, ['metric', 'value', 'unit', 'state', 'source', 'scope', 'definition_and_limits', 'observed_at'], ',', '"', '');
            foreach ($rows as $row) {
                fputcsv($file, $row, ',', '"', '');
            }
            fclose($file);
        }, 'nadi-ringkasan-'.now()->format('Ymd-His').'.csv', ['Content-Type' => 'text/csv; charset=UTF-8', 'Cache-Control' => 'no-store, private']);
    }
}

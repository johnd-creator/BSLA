<?php

namespace App\Http\Controllers;

use App\Services\DataOverview;
use App\Services\ReliabilityMart;

class OverviewController extends Controller
{
    public function index(DataOverview $overview, ReliabilityMart $mart)
    {
        return view('home', ['snapshot' => $overview->snapshot($mart)]);
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

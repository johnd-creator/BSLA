<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;
use App\Models\User;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use PDO;
use Tests\TestCase;

class ReliabilitySnapshotConsistencyTest extends TestCase
{
    public function test_concurrent_correction_cannot_mix_observation_and_review_versions(): void
    {
        // A separate synthetic SQLite file exercises actual WAL readers/writers.
        // Never configure, migrate or write the normal development store here.
        $file = tempnam(sys_get_temp_dir(), 'nadi-reliability-consistency-');
        $this->assertNotFalse($file);
        chmod($file, 0600);
        config(['database.default' => 'sqlite', 'database.connections.sqlite.database' => $file, 'database.connections.sqlite.url' => null]);
        DB::purge('sqlite');
        $writer = null;
        try {
            $this->assertSame($file, DB::connection()->getDatabaseName());
            Artisan::call('migrate', ['--force' => true]);
            DB::statement('PRAGMA journal_mode=WAL');
            $owner = User::factory()->create();
            $asset = 'asset:MAXIMO:MXASSET:BSR:IP:CONSISTENCY-QA';
            $event = AssetDisruption::create(['created_by' => $owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => $asset, 'event_type' => 'trip', 'description' => 'Synthetic consistency test', 'impact' => 'unknown', 'occurred_on' => '2026-02-01']);
            $event->members()->create(['asset_ref' => $asset, 'role' => 'unknown']);
            $review = ReliabilityReview::create(['asset_disruption_id' => $event->id, 'asset_ref' => $asset, 'revision' => 1, 'event_version' => 1, 'created_by' => $owner->id, 'request_key' => (string) Str::uuid(), 'classification' => 'failure', 'required_function' => 'Synthetic function', 'evidence' => 'Synthetic initial evidence', 'reason' => 'Synthetic first review', 'repair_state' => 'unknown', 'active_intervals' => [], 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now()]);
            $next = $review->getAttributes();
            unset($next['id']);
            $next = array_replace($next, ['revision' => 2, 'event_version' => 2, 'request_key' => (string) Str::uuid(), 'classification' => 'not_failure', 'reason' => 'Synthetic concurrent correction']);
            $writer = new PDO('sqlite:'.$file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
            $writer->exec('PRAGMA busy_timeout=3000');
            $corrected = false;
            DB::listen(function ($query) use (&$writer, $event, $next, &$corrected) {
                if (! $corrected && str_starts_with($query->sql, 'select * from "asset_disruptions"')) {
                    $corrected = true;
                    $writer->beginTransaction();
                    $writer->prepare('UPDATE asset_disruptions SET version=2 WHERE id=?')->execute([$event->id]);
                    $columns = implode(',', array_keys($next));
                    $values = implode(',', array_fill(0, count($next), '?'));
                    $writer->prepare('INSERT INTO reliability_reviews ('.$columns.') VALUES ('.$values.')')->execute(array_values($next));
                    $writer->commit();
                }
            });
            config(['services.reliability_mart.url' => 'http://consistency.test']);
            Http::preventStrayRequests();
            Http::fake(function () {
                $this->assertSame(0, DB::connection()->transactionLevel(), 'Source HTTP must not hold a local read transaction.');
                $this->assertFalse(DB::connection()->getPdo()->inTransaction());

                return Http::response([], 503);
            });
            $before = app(ReliabilityEvidence::class)->report($asset, 2026, app(ReliabilityMart::class));
            $this->assertTrue($corrected);
            $this->assertSame(1, $before['events'][0]['event_version']);
            $this->assertSame(1, $before['events'][0]['review_revision']);
            $this->assertSame('failure', $before['events'][0]['state']);
            $after = app(ReliabilityEvidence::class)->report($asset, 2026, app(ReliabilityMart::class));
            $this->assertSame(2, $after['events'][0]['event_version']);
            $this->assertSame(2, $after['events'][0]['review_revision']);
            $this->assertSame('not_failure', $after['events'][0]['state']);
            $this->assertNotSame($before['evidence_hash'], $after['evidence_hash']);
            $throwNext = true;
            DB::listen(function ($query) use (&$throwNext) {
                if ($throwNext && str_starts_with($query->sql, 'select * from "asset_disruptions"')) {
                    $throwNext = false;
                    throw new \RuntimeException('Synthetic interrupted evidence read');
                }
            });
            try {
                app(ReliabilityEvidence::class)->report($asset, 2026, app(ReliabilityMart::class));
                $this->fail('The interrupted read unexpectedly succeeded.');
            } catch (\RuntimeException $error) {
                $this->assertSame('Synthetic interrupted evidence read', $error->getMessage());
            }
            $this->assertFalse(DB::connection()->getPdo()->inTransaction());
            $this->assertSame('IMMEDIATE', DB::connection()->getConfig('transaction_mode'));

        } finally {
            DB::disconnect('sqlite');
            $writer = null;
            foreach ([$file, $file.'-wal', $file.'-shm'] as $temporary) {
                if (is_file($temporary)) {
                    unlink($temporary);
                }
            }
        }
    }
}

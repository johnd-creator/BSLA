<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Tests\TestCase;

class PdmDateMigrationTest extends TestCase
{
    public function test_upgrade_and_safe_rollback_preserve_existing_instants_links_and_values(): void
    {
        $originalConnection = DB::getDefaultConnection();
        $originalSchema = Schema::getFacadeRoot();
        config(['database.connections.precision_migration' => ['driver' => 'sqlite', 'database' => ':memory:', 'foreign_key_constraints' => true]]);
        DB::setDefaultConnection('precision_migration');
        Schema::swap(DB::connection('precision_migration')->getSchemaBuilder());
        try {
            foreach (glob(database_path('migrations/*.php')) as $file) {
                if (str_ends_with($file, 'support_pdm_date_precision.php')) {
                    continue;
                }
                (require $file)->up();
            }
            DB::table('users')->insert(['id' => 1, 'name' => 'Fixture', 'email' => 'fixture@example.test', 'password' => 'not-a-login']);
            $legacy = ['id' => 1, 'created_by' => 1, 'request_key' => 'e52a005b-07a5-46c8-bf72-79a9ff22e141', 'title' => 'Legacy timestamp', 'asset_ref' => 'asset:test', 'template_id' => 'test', 'template_fingerprint' => str_repeat('a', 64), 'method' => 'VIBRATION', 'measured_at' => '2026-07-07 17:15:37', 'timezone' => 'Asia/Jakarta', 'instrument' => 'Legacy meter', 'measurement_mode' => 'RMS', 'operating_condition' => 'Legacy condition', 'asset_selection_note' => 'Legacy evidence', 'template_snapshot' => '{"legacy":true}', 'readings' => '{"p1":{"value":"0","unit":"mm/s"}}', 'version' => 3];
            DB::table('pdm_activities')->insert($legacy);
            DB::table('inspection_drafts')->insert(['id' => 1, 'created_by' => 1, 'pdm_activity_id' => 1, 'request_reference' => 'Legacy linked', 'request_summary' => 'Preserve link']);
            $migration = require database_path('migrations/2026_11_07_000002_support_pdm_date_precision.php');
            $migration->up();
            $row = (array) DB::table('pdm_activities')->first();
            foreach ($legacy as $key => $value) {
                $this->assertSame($value, $row[$key], $key);
            }
            $this->assertSame('datetime', $row['time_precision']);
            $this->assertSame('2026-07-08', $row['measured_on']);
            $this->assertSame(1, DB::table('inspection_drafts')->value('pdm_activity_id'));
            $this->assertCount(0, DB::select('PRAGMA foreign_key_check'));
            $migration->down();
            $this->assertFalse(Schema::hasColumn('pdm_activities', 'time_precision'));
            $this->assertSame('2026-07-07 17:15:37', DB::table('pdm_activities')->value('measured_at'));
            $migration->up();
            $this->assertSame('2026-07-08', DB::table('pdm_activities')->value('measured_on'));
            $this->assertSame(1, DB::table('inspection_drafts')->value('pdm_activity_id'));
            $this->assertCount(0, DB::select('PRAGMA foreign_key_check'));
        } finally {
            Schema::swap($originalSchema);
            DB::setDefaultConnection($originalConnection);
            DB::purge('precision_migration');
        }
    }
}

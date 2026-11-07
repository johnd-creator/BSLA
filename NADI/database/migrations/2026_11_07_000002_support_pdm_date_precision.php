<?php

use Carbon\CarbonImmutable;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pdm_activities', function (Blueprint $table) {
            $table->string('time_precision', 12)->default('datetime');
            $table->date('measured_on')->nullable();
            $table->dateTime('measured_at')->nullable()->change();
            $table->string('timezone', 60)->nullable()->change();
            $table->index(['asset_ref', 'template_id', 'measured_on'], 'pdm_activity_date_history');
        });
        // Existing instants retain their exact UTC time and declared zone. Derive
        // only the calendar date; never manufacture an instant for a date-only row.
        DB::table('pdm_activities')->select(['id', 'measured_at', 'timezone'])->orderBy('id')->chunkById(100, function ($rows) {
            foreach ($rows as $row) {
                DB::table('pdm_activities')->where('id', $row->id)->update([
                    'measured_on' => CarbonImmutable::parse($row->measured_at, 'UTC')->setTimezone($row->timezone)->format('Y-m-d'),
                ]);
            }
        });
    }

    public function down(): void
    {
        // A rollback must not invent midnight/UTC or discard date-only records.
        if (DB::table('pdm_activities')->whereNull('measured_at')->orWhereNull('timezone')->exists()) {
            throw new RuntimeException('Rollback blocked: date-only PdM records need an explicit preservation plan.');
        }
        Schema::table('pdm_activities', function (Blueprint $table) {
            $table->dropIndex('pdm_activity_date_history');
            $table->dropColumn(['time_precision', 'measured_on']);
            $table->dateTime('measured_at')->nullable(false)->change();
            $table->string('timezone', 60)->nullable(false)->change();
        });
    }
};

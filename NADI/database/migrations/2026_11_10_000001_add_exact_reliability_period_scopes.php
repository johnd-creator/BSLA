<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        foreach (['reliability_policies', 'reliability_approvals', 'asset_wellness_policies'] as $name) {
            Schema::table($name, function (Blueprint $table) {
                // Null preserves the legacy annual scope and its immutable rows.
                $table->string('period_key', 70)->nullable();
                $table->index(['asset_ref', 'year', 'period_key', 'revision']);
            });
        }
    }

    public function down(): void
    {
        $names = ['reliability_policies', 'reliability_approvals', 'asset_wellness_policies'];
        foreach ($names as $name) {
            if (DB::table($name)->whereNotNull('period_key')->exists()) {
                throw new RuntimeException('Period history exists. Preserve it and use a forward-compatible migration.');
            }
        }
        foreach ($names as $name) {
            Schema::table($name, function (Blueprint $table) {
                $table->dropIndex(['asset_ref', 'year', 'period_key', 'revision']);
                $table->dropColumn('period_key');
            });
        }
    }
};

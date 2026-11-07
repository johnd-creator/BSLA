<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pdm_activities', function (Blueprint $table) {
            $table->string('inspection_type', 20)->nullable();
            $table->string('requester_name', 200)->nullable();
            $table->string('request_reference', 100)->nullable();
            $table->string('request_summary', 200)->nullable();
        });
        Schema::table('inspection_drafts', function (Blueprint $table) {
            $table->uuid('request_key')->nullable()->unique();
            $table->foreignId('pdm_activity_id')->nullable()->unique()->constrained('pdm_activities');
            $table->string('inspection_type', 20)->default('request');
            $table->string('requester_name', 200)->nullable();
            $table->string('follow_up_status', 20)->default('open');
        });
    }

    public function down(): void
    {
        Schema::table('inspection_drafts', function (Blueprint $table) {
            $table->dropForeign(['pdm_activity_id']);
            $table->dropUnique(['pdm_activity_id']);
            $table->dropUnique(['request_key']);
            $table->dropColumn(['request_key', 'pdm_activity_id', 'inspection_type', 'requester_name', 'follow_up_status']);
        });
        Schema::table('pdm_activities', function (Blueprint $table) {
            $table->dropColumn(['inspection_type', 'requester_name', 'request_reference', 'request_summary']);
        });
    }
};

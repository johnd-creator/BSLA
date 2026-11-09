<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pdm_inspection_plans', function (Blueprint $table) {
            $table->id();
            $table->string('request_key', 36)->unique();
            $table->string('identity_key', 64)->unique();
            $table->foreignId('created_by')->constrained('users')->restrictOnDelete();
            $table->string('title', 200);
            $table->string('asset_ref', 240)->index();
            $table->string('template_id', 100);
            $table->string('template_fingerprint', 64);
            $table->json('template_snapshot');
            $table->string('point_key', 100);
            $table->string('method', 40);
            $table->string('unit', 40)->nullable();
            $table->string('instrument', 200);
            $table->string('measurement_mode', 200);
            $table->string('operating_condition', 200);
            $table->text('asset_selection_note');
            $table->unsignedInteger('frequency_value');
            $table->string('frequency_unit', 12);
            $table->date('first_due_on');
            $table->string('status', 12)->default('active')->index();
            $table->text('notes')->nullable();
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
        });
        Schema::create('pdm_inspection_plan_revisions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('plan_id')->constrained('pdm_inspection_plans')->restrictOnDelete();
            $table->foreignId('actor_id')->constrained('users')->restrictOnDelete();
            $table->unsignedInteger('version');
            $table->text('reason');
            $table->json('snapshot');
            $table->timestamp('created_at');
            $table->unique(['plan_id', 'version']);
        });
    }

    public function down(): void
    {
        if (DB::table('pdm_inspection_plans')->exists()) {
            throw new RuntimeException('Rollback ditolak: rencana dan riwayat PdM harus dipertahankan.');
        }
        Schema::dropIfExists('pdm_inspection_plan_revisions');
        Schema::dropIfExists('pdm_inspection_plans');
    }
};

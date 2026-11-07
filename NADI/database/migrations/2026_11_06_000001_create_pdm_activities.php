<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pdm_activities', function (Blueprint $table) {
            $table->id();
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('title', 200);
            $table->string('asset_ref', 240);
            $table->string('template_id', 100);
            $table->string('template_fingerprint', 64);
            $table->string('method', 40);
            $table->dateTime('measured_at');
            $table->string('timezone', 60);
            $table->string('operating_condition', 200);
            $table->string('instrument', 200);
            $table->string('measurement_mode', 200);
            $table->text('asset_selection_note');
            $table->text('notes')->nullable();
            $table->json('template_snapshot');
            $table->json('readings');
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
            $table->index(['asset_ref', 'template_id', 'measured_at'], 'pdm_activity_history');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('pdm_activities');
    }
};

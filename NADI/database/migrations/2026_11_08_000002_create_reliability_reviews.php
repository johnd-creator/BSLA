<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('reliability_reviews', function (Blueprint $table) {
            $table->id();
            $table->foreignId('asset_disruption_id')->constrained();
            $table->string('asset_ref', 240);
            $table->unsignedInteger('revision');
            $table->unsignedInteger('event_version');
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('classification', 30);
            $table->foreignId('duplicate_of')->nullable()->constrained('asset_disruptions');
            $table->unsignedInteger('duplicate_version')->nullable();
            $table->unsignedInteger('duplicate_review_revision')->nullable();
            $table->text('required_function')->nullable();
            $table->text('evidence');
            $table->text('reason');
            $table->dateTime('failure_at')->nullable();
            $table->dateTime('restored_at')->nullable();
            $table->string('repair_state', 30)->default('unknown');
            $table->json('active_intervals');
            $table->text('timing_evidence')->nullable();
            $table->string('rule_version', 50);
            $table->json('event_snapshot');
            $table->timestamp('created_at');
            $table->unique(['asset_disruption_id', 'asset_ref', 'revision'], 'reliability_review_revision');
            $table->index(['asset_ref', 'asset_disruption_id']);
        });
        Schema::create('reliability_snapshots', function (Blueprint $table) {
            $table->id();
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('asset_ref', 240);
            $table->unsignedSmallInteger('year');
            $table->string('rule_version', 50);
            $table->string('evidence_hash', 64);
            $table->json('report');
            $table->timestamp('created_at');
            $table->index(['asset_ref', 'year']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reliability_snapshots');
        Schema::dropIfExists('reliability_reviews');
    }
};

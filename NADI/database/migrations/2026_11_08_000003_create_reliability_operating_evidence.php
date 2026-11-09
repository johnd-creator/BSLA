<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('operating_logs', function (Blueprint $table) {
            $table->id();
            $table->string('asset_ref', 240)->index();
            $table->foreignId('created_by')->constrained('users');
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
        });
        Schema::create('operating_log_revisions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('operating_log_id')->constrained();
            $table->unsignedInteger('revision');
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->dateTime('started_at');
            $table->dateTime('ended_at');
            $table->string('state', 20);
            $table->string('review_state', 20);
            $table->text('source');
            $table->text('evidence');
            $table->text('reason');
            $table->timestamp('created_at');
            $table->unique(['operating_log_id', 'revision']);
        });
        Schema::create('reliability_policies', function (Blueprint $table) {
            $table->id();
            $table->string('asset_ref', 240);
            $table->unsignedSmallInteger('year');
            $table->unsignedInteger('revision');
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->json('rules');
            $table->text('evidence');
            $table->text('reason');
            $table->timestamp('created_at');
            $table->unique(['asset_ref', 'year', 'revision']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reliability_policies');
        Schema::dropIfExists('operating_log_revisions');
        Schema::dropIfExists('operating_logs');
    }
};

<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('asset_disruptions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('asset_ref', 240);
            $table->string('event_type', 30);
            $table->text('description');
            $table->text('known_cause')->nullable();
            $table->string('impact', 30);
            $table->text('impact_note')->nullable();
            $table->date('occurred_on')->nullable();
            $table->dateTime('occurred_at')->nullable();
            $table->date('restored_on')->nullable();
            $table->dateTime('restored_at')->nullable();
            $table->string('timezone', 60)->nullable();
            $table->string('work_order_ref', 200)->nullable();
            $table->text('evidence_note')->nullable();
            $table->string('status', 20)->default('recorded');
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
            $table->index(['status', 'occurred_on']);
        });
        Schema::create('asset_disruption_members', function (Blueprint $table) {
            $table->id();
            $table->foreignId('asset_disruption_id')->constrained();
            $table->string('asset_ref', 240);
            $table->string('role', 20);
            $table->unique(['asset_disruption_id', 'asset_ref'], 'disruption_unique_member');
            $table->index('asset_ref');
        });
        Schema::create('asset_disruption_revisions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('asset_disruption_id')->constrained();
            $table->foreignId('changed_by')->constrained('users');
            $table->unsignedInteger('version');
            $table->text('reason');
            $table->json('snapshot');
            $table->timestamp('created_at');
            $table->unique(['asset_disruption_id', 'version'], 'disruption_unique_revision');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('asset_disruption_revisions');
        Schema::dropIfExists('asset_disruption_members');
        Schema::dropIfExists('asset_disruptions');
    }
};

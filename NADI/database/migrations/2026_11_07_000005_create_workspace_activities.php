<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        foreach (['asset_priority_revisions', 'asset_disruption_revisions', 'pdm_activities', 'inspection_drafts'] as $name) {
            Schema::table($name, fn (Blueprint $table) => $table->index(['created_at', 'id'], $name.'_feed_order'));
        }
        Schema::create('workspace_activities', function (Blueprint $table) {
            $table->id();
            $table->string('kind', 20);
            $table->unsignedBigInteger('subject_id');
            $table->unsignedInteger('version');
            $table->foreignId('actor_id')->constrained('users');
            $table->string('asset_ref', 240)->nullable();
            $table->string('action', 30);
            $table->json('changes');
            $table->timestamp('created_at');
            $table->unique(['kind', 'subject_id', 'version']);
            $table->index(['created_at', 'id']);
            $table->index(['kind', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('workspace_activities');
        foreach (['asset_priority_revisions', 'asset_disruption_revisions', 'pdm_activities', 'inspection_drafts'] as $name) {
            Schema::table($name, fn (Blueprint $table) => $table->dropIndex($name.'_feed_order'));
        }
    }
};

<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('asset_priorities', function (Blueprint $table) {
            $table->id();
            $table->string('asset_ref', 240)->unique();
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('urgency', 20);
            $table->string('status', 20)->default('active');
            $table->text('observed_condition');
            $table->text('impact');
            $table->text('reasoning');
            $table->text('evidence_note');
            $table->string('owner', 120);
            $table->date('due_on')->nullable();
            $table->date('review_on')->nullable();
            $table->foreignId('disruption_id')->nullable()->constrained('asset_disruptions');
            $table->foreignId('inspection_id')->nullable()->constrained('inspection_drafts');
            $table->string('work_order_ref', 200)->nullable();
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
            $table->index(['status', 'urgency', 'review_on']);
        });
        Schema::create('asset_priority_revisions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('asset_priority_id')->constrained();
            $table->foreignId('changed_by')->constrained('users');
            $table->unsignedInteger('version');
            $table->text('reason');
            $table->json('snapshot');
            $table->timestamp('created_at');
            $table->unique(['asset_priority_id', 'version']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('asset_priority_revisions');
        Schema::dropIfExists('asset_priorities');
    }
};

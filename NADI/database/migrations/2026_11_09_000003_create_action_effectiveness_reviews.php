<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('action_effectiveness_reviews', function (Blueprint $table) {
            $table->id();
            $table->foreignId('inspection_draft_id')->constrained();
            $table->unsignedInteger('revision');
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->foreignId('before_activity_id')->nullable()->constrained('pdm_activities');
            $table->foreignId('after_activity_id')->nullable()->constrained('pdm_activities');
            $table->text('action_taken');
            $table->date('completed_on');
            $table->string('point', 120)->nullable();
            $table->string('decision', 30);
            $table->text('reason');
            $table->json('evidence');
            $table->timestamp('created_at');
            $table->unique(['inspection_draft_id', 'revision']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('action_effectiveness_reviews');
    }
};

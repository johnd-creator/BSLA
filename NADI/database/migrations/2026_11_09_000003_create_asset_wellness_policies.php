<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('asset_wellness_policies', function (Blueprint $table) {
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
        Schema::dropIfExists('asset_wellness_policies');
    }
};

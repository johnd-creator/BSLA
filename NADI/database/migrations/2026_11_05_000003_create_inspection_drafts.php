<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('inspection_drafts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('created_by')->constrained('users');
            $table->string('request_reference', 100);
            $table->string('request_summary', 200);
            $table->string('asset_ref', 240)->nullable();
            $table->string('method', 40)->nullable();
            $table->date('inspected_on')->nullable();
            $table->text('finding')->nullable();
            $table->text('recommendation')->nullable();
            $table->date('target_completion')->nullable();
            $table->string('wo_reference', 100)->nullable();
            $table->unsignedInteger('version')->default(1);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('inspection_drafts');
    }
};

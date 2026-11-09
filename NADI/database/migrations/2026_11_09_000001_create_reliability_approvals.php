<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('reliability_approvals', function (Blueprint $table) {
            $table->id();
            $table->string('asset_ref', 240);
            $table->unsignedSmallInteger('year');
            $table->unsignedInteger('revision');
            $table->foreignId('reliability_snapshot_id')->constrained();
            $table->foreignId('created_by')->constrained('users');
            $table->uuid('request_key')->unique();
            $table->string('decision', 20);
            $table->string('actor_role', 20);
            $table->json('metrics');
            $table->boolean('method_attestation');
            $table->boolean('result_attestation');
            $table->string('engine_version', 80);
            $table->unsignedBigInteger('policy_id');
            $table->unsignedInteger('policy_revision');
            $table->string('basis_hash', 64);
            $table->string('calculation_hash', 64);
            $table->string('snapshot_evidence_hash', 64);
            $table->text('evidence');
            $table->text('reason');
            $table->json('approved_values');
            $table->timestamp('created_at');
            $table->unique(['asset_ref', 'year', 'revision']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reliability_approvals');
    }
};

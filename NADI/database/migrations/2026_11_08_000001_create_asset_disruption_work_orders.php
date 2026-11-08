<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('asset_disruption_work_orders', function (Blueprint $table) {
            $table->id();
            $table->foreignId('asset_disruption_id')->constrained();
            $table->string('asset_ref', 240);
            $table->string('work_order_ref', 200);
            $table->string('record_ref', 200);
            $table->string('relation_state', 20)->default('uncertain');
            $table->text('note')->nullable();
            $table->timestamp('identity_checked_at');
            $table->timestamps();
            $table->unique(['asset_disruption_id', 'work_order_ref'], 'disruption_unique_work_order');
            $table->index(['work_order_ref', 'asset_ref'], 'disruption_work_order_lookup');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('asset_disruption_work_orders');
    }
};

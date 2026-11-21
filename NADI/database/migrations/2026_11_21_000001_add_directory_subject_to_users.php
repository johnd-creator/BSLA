<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('directory_subject', 64)->nullable()->unique();
        });
    }

    public function down(): void
    {
        if (DB::table('users')->whereNotNull('directory_subject')->exists()) {
            throw new RuntimeException('Directory identities exist; preserve their account bindings.');
        }
        Schema::table('users', function (Blueprint $table) {
            $table->dropUnique(['directory_subject']);
            $table->dropColumn('directory_subject');
        });
    }
};

<?php

use App\Enums\Role;
use App\Models\User;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

Artisan::command('nadi:admin {--email=} {--name=Developer}', function () {
    if (! app()->environment('local') || config('database.default') !== 'sqlite' || realpath(config('database.connections.sqlite.database')) !== realpath(database_path('development.sqlite'))) {
        $this->error('Bootstrap hanya untuk database SQLite development lokal.');

        return 1;
    }
    $email = Str::lower(trim($this->option('email') ?: $this->ask('Email administrator')));
    if (! filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $this->error('Email tidak valid.');

        return 1;
    }
    $credentialFile = storage_path('app/private/development-login.txt');
    if (file_exists($credentialFile)) {
        $this->error('File login development sudah ada. Bootstrap tidak diulang.');

        return 1;
    }
    $password = bin2hex(random_bytes(18));
    DB::transaction(function () use ($email, $password) {
        if (User::query()->exists()) {
            throw new RuntimeException('Bootstrap hanya untuk tabel akun yang kosong.');
        }
        $user = new User;
        $user->name = $this->option('name');
        $user->email = $email;
        $user->password = $password;
        $user->roles = [Role::Admin->value];
        $user->save();
    });
    if (! is_dir(dirname($credentialFile))) {
        mkdir(dirname($credentialFile), 0700, true);
    }
    $handle = fopen($credentialFile, 'x');
    chmod($credentialFile, 0600);
    fwrite($handle, "NADI development only\nURL: http://127.0.0.1:8010/login\nEmail: {$email}\nPassword: {$password}\n");
    fclose($handle);
    $this->info('Administrator development dibuat. Baca kredensial hanya di file lokal privat:');
    $this->line($credentialFile);
})->purpose('Bootstrap one administrator for the isolated local development database');

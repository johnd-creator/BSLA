<?php

namespace App\Console\Commands;

use App\Enums\Role;
use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class CreateDevelopmentUsers extends Command
{
    protected $signature = 'nadi:dev-users {--memorable : Generate an easy-to-remember development phrase}';

    protected $description = 'Create four local-only development accounts without replacing any existing account';

    public function handle(): int
    {
        $host = parse_url(config('app.url'), PHP_URL_HOST);
        if (! app()->environment('local') || ! in_array($host, ['127.0.0.1', 'localhost', '::1'], true)
            || config('database.default') !== 'sqlite'
            || realpath(config('database.connections.sqlite.database')) !== realpath(database_path('development.sqlite'))) {
            $this->error('Perintah ini hanya untuk SQLite development dan APP_URL loopback lokal.');

            return self::FAILURE;
        }
        $path = storage_path('app/private/development-users.txt');
        if (file_exists($path)) {
            $this->error('File akun development sudah ada. Tidak ada akun/password yang diubah.');

            return self::FAILURE;
        }
        if (! is_dir(dirname($path))) {
            mkdir(dirname($path), 0700, true);
        }
        $handle = fopen($path, 'x');
        if (! $handle) {
            $this->error('File privat tidak dapat dibuat.');

            return self::FAILURE;
        }
        chmod($path, 0600);
        $words = ['kopi', 'pagi', 'biru', 'langit', 'buku', 'hujan', 'pohon', 'bulan'];
        $password = $this->option('memorable')
            ? implode('-', array_map(fn ($index) => $words[$index], array_rand($words, 3))).'-'.random_int(1000, 9999)
            : bin2hex(random_bytes(18));
        $content = "NADI LOCAL DEVELOPMENT ONLY\nURL: http://127.0.0.1:8010/login\nShared development password: {$password}\n\n";
        try {
            DB::transaction(function () use ($password, &$content) {
                foreach (Role::cases() as $role) {
                    $username = strtolower($role->value);
                    if (User::where('username', $username)->orWhere('email', $username.'@nadi.local')->exists()) {
                        throw new \RuntimeException('Akun tujuan sudah ada. Tidak ada akun/password yang ditimpa.');
                    }
                    $user = new User;
                    $user->name = $role->label();
                    $user->username = $username;
                    $user->email = $username.'@nadi.local';
                    $user->password = $password;
                    $user->roles = [$role->value];
                    $user->development_only = true;
                    $user->save();
                    $content .= "Username: {$username} | Role: {$role->label()}\n";
                }
            });
            $content .= "\nUbah password lewat User management > Kelola (Admin). File ini hanya mencatat password awal.\n";
            if (fwrite($handle, $content) !== strlen($content)) {
                throw new \RuntimeException('Penulisan file privat gagal.');
            }
        } catch (\Throwable $error) {
            fclose($handle);
            unlink($path);
            $this->error('Pembuatan akun development gagal. Periksa konfigurasi atau akun yang sudah ada.');

            return self::FAILURE;
        }
        fclose($handle);
        $this->info('Empat akun development dibuat. Kredensial hanya di file lokal privat:');
        $this->line($path);

        return self::SUCCESS;
    }
}

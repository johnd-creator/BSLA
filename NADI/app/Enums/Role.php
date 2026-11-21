<?php

namespace App\Enums;

enum Role: string
{
    case Admin = 'ADMIN';
    case Engineer = 'ENGINEER';
    case Supervisor = 'SUPERVISOR';
    case Manager = 'MANAGER';

    case Viewer = 'VIEWER';

    /** @return list<self> */
    public static function localRoles(): array
    {
        return [self::Admin, self::Engineer, self::Supervisor, self::Manager];
    }

    public function label(): string
    {
        return ucfirst(strtolower($this->value));
    }

    public function description(): string
    {
        return match ($this) {
            self::Admin => 'Membaca workspace serta mengelola akun dan role.',
            self::Engineer => 'Membaca Asset, backlog WAPPR, dan draft Action Board. Dapat menyusun draft inspeksi/rekomendasi milik sendiri; bukan analisis tervalidasi.',
            self::Supervisor => 'Membaca workspace dan mengesahkan metode serta hasil reliability pada snapshot. Persetujuan pekerjaan belum aktif.',
            self::Viewer => 'Hanya dapat membuka halaman sambutan tanpa data operasional.',
            self::Manager => 'Membaca Asset, backlog WAPPR, dan draft Action Board. Persetujuan anggaran dan risiko belum aktif.',
        };
    }
}

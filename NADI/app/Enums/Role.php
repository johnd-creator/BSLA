<?php

namespace App\Enums;

enum Role: string
{
    case Admin = 'ADMIN';
    case Engineer = 'ENGINEER';
    case Supervisor = 'SUPERVISOR';
    case Manager = 'MANAGER';

    public function label(): string
    {
        return ucfirst(strtolower($this->value));
    }

    public function description(): string
    {
        return match ($this) {
            self::Admin => 'Membaca workspace serta mengelola akun dan role.',
            self::Engineer => 'Membaca Asset, backlog WAPPR, dan draft Action Board. Dapat menyusun draft inspeksi/rekomendasi milik sendiri; bukan analisis tervalidasi.',
            self::Supervisor => 'Membaca Asset, backlog WAPPR, dan draft Action Board. Persetujuan pekerjaan belum aktif.',
            self::Manager => 'Membaca Asset, backlog WAPPR, dan draft Action Board. Persetujuan anggaran dan risiko belum aktif.',
        };
    }
}

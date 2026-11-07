<?php

namespace App\Services;

use RuntimeException;

class PdmFormCatalog
{
    public const METHODS = ['VIBRATION' => 'Vibrasi', 'TRIBOLOGY' => 'Tribology / oli', 'MCSA' => 'MCSA', 'CONDITION_MONITORING' => 'Condition monitoring', 'THERMOGRAPHY' => 'Thermography'];

    private ?array $catalog = null;

    public function all(): array
    {
        if ($this->catalog === null) {
            $path = config('pdm.catalog');
            if (! is_string($path) || $path === '') {
                throw new RuntimeException('Konfigurasi katalog form PdM tidak valid.');
            }
            if (! is_file($path) || ! is_readable($path)) {
                return [];
            }
            $data = json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR);
            if (! is_array($data['templates'] ?? null)) {
                throw new RuntimeException('Katalog form PdM tidak valid.');
            }
            $this->catalog = $data['templates'];
        }

        return $this->catalog;
    }

    public function find(string $id): array
    {
        foreach ($this->all() as $template) {
            if ($template['id'] === $id) {
                return $template;
            }
        }
        abort(404, 'Template PdM tidak ditemukan.');
    }

    public function forAsset(string $asset): array
    {
        return array_values(array_filter($this->all(), fn ($template) => in_array($asset, array_column($template['candidates'], 'canonical_id'), true)));
    }

    public function fingerprint(array $template): string
    {
        return hash('sha256', json_encode($this->snapshot($template), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
    }

    public function snapshot(array $template): array
    {
        return array_intersect_key($template, array_flip(['id', 'title', 'method', 'source', 'status', 'review_notes', 'fields', 'preview_only', 'binding_status', 'field_extraction_status']));
    }
}

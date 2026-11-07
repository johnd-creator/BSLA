<?php

namespace App\Services;

use Throwable;

class BsrAssetMapping
{
    public function snapshot(): ?array
    {
        $path = config('services.asset_mapping.file');
        if (! is_string($path) || ! is_file($path) || filesize($path) > 8388608) {
            return null;
        }
        try {
            $data = json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR);
            if (($data['state'] ?? null) !== 'DRAFT_NOT_APPLIED' || ($data['scope'] ?? null) !== ['site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01'] || ! is_array($data['assets'] ?? null)) {
                return null;
            }
            foreach ($data['assets'] as $asset) {
                if (! is_array($asset) || ! is_string($asset['canonical_id'] ?? null) || ($asset['source']['site_code'] ?? null) !== 'BSR' || ($asset['source']['organization_code'] ?? null) !== 'IP' || ($asset['source']['unit'] ?? null) !== 'CS01') {
                    return null;
                }
            }

            return $data;
        } catch (Throwable) {
            return null;
        }
    }

    public function forAsset(array $source): ?array
    {
        if (($source['site_code'] ?? null) !== 'BSR' || ($source['organization_code'] ?? null) !== 'IP' || ($source['unit'] ?? null) !== 'CS01') {
            return null;
        }
        foreach ($this->snapshot()['assets'] ?? [] as $entry) {
            if ($entry['canonical_id'] === ($source['canonical_id'] ?? null) && $entry['source']['source_asset_number'] === ($source['source_asset_number'] ?? null)) {
                return $entry;
            }
        }

        return null;
    }
}

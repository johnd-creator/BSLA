<?php

namespace App\Services;

use Throwable;

class CemsAssetMapping
{
    public function resolve(array $parameters, ReliabilityMart $mart): array
    {
        $configured = config('cems.asset_mappings', []);
        $links = [];
        $records = [];
        foreach (array_slice($parameters, 0, 32) as $row) {
            $code = $row['parameter_code'];
            $mapping = $configured[$code] ?? null;
            if (! is_array($mapping) || ($mapping['verified'] ?? false) !== true
                || ! is_string($mapping['canonical_id'] ?? null) || strlen($mapping['canonical_id']) > 160
                || ! is_string($mapping['kks'] ?? null) || $mapping['kks'] === '' || strlen($mapping['kks']) > 100
                || ! is_string($mapping['evidence'] ?? null) || trim($mapping['evidence']) === '') {
                continue;
            }
            try {
                $id = $mapping['canonical_id'];
                if (! array_key_exists($id, $records)) {
                    $records[$id] = null;
                    $records[$id] = $mart->inventoryDetail($id);
                }
                $asset = $records[$id];
                if (($asset['canonical_id'] ?? null) === $mapping['canonical_id'] && ($asset['source_asset_number'] ?? null) === $mapping['kks']) {
                    $links[$code] = ['canonical_id' => $mapping['canonical_id'], 'kks' => $mapping['kks']];
                }
            } catch (Throwable) {
                // Never expose an unavailable or mismatched asset link.
            }
        }

        return $links;
    }
}

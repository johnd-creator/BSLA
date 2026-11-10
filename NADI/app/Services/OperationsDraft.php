<?php

namespace App\Services;

/** Display labels from the existing BOIL draft, never asset or historian mappings. */
class OperationsDraft
{
    public const SCREENS = ['BOIL', 'TURB', 'ECS', 'DEH', 'CCS', 'FSSS', 'CHM', 'MEH'];

    public static function components(): array
    {
        $components = [];
        foreach (['G', 'F', 'E', 'D', 'C', 'B', 'A'] as $mill) {
            $components['mill-'.strtolower($mill)] = [
                'label' => 'MILL '.$mill,
                'group' => 'Coal & Mill',
                'units' => ['%', '%', 't/h', 'A'],
            ];
        }
        $components['drum'] = ['label' => 'DRUM', 'group' => 'Boiler & Steam', 'units' => ['MPa', 'mm', 'mm']];
        $components['scan-fan'] = ['label' => 'SCAN FAN A / B', 'group' => 'Boiler & Steam', 'units' => ['kPa', 'kPa']];
        foreach (['PAF A', 'PAF B', 'IDF A', 'IDF B', 'FDF A', 'FDF B'] as $fan) {
            $components[strtolower(str_replace(' ', '-', $fan))] = ['label' => $fan, 'group' => 'Air & Flue Gas', 'units' => ['A']];
        }
        foreach (['BFP B', 'BFP A', 'BFSP'] as $pump) {
            $components[strtolower(str_replace(' ', '-', $pump))] = ['label' => $pump, 'group' => 'Feedwater', 'units' => ['%', 'A']];
        }

        return $components;
    }
}

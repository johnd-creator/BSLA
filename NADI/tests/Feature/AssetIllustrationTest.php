<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\AssetIllustration;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class AssetIllustrationTest extends TestCase
{
    use RefreshDatabase;

    #[DataProvider('clearCabinets')]
    public function test_only_clear_equipment_cabinets_receive_a_local_generic_illustration(string $description): void
    {
        $asset = ['canonical_id' => 'asset:BSR:VISUAL', 'description' => $description, 'hierarchy_category' => 'equipment'];
        $before = $asset;
        $result = app(AssetIllustration::class)->forAsset($asset);
        $this->assertSame($before, $asset);
        $this->assertSame('control-cabinet', $result['family']);
        $this->assertSame('GENERIC_AI_ILLUSTRATION', $result['kind']);
        $this->assertSame('NOT_ENGINEER_VERIFIED', $result['review_status']);
        $this->assertSame('/images/asset-families/control-cabinet-illustration-v1.png', $result['path']);
        $this->assertFileExists(public_path(ltrim($result['path'], '/')));
    }

    public static function clearCabinets(): array
    {
        return array_map(fn ($description) => [$description], [
            'METS CABINET',
            'MTSI CABINET',
            'FIRE PUMP STATION MCC',
            'FAN VIBRATION MONITORING CABINET',
            'GENERATOR TRANSFORMER UNIT PROTECTION PANEL',
            'GENERATOR TRANSFORMER FAULT WAVEFORM-RECORDING PANEL',
            'FUEL OIL PUMP HOUSE DCS RI/O CABINET',
            'CONTROL PANEL A',
            'ESP A HIGH VOLTAGE (HV) CONTROL CABINET FIELD 1',
            'ESP B HIGH VOLTAGE (HV) CONTROL CABINET FIELD 4',
            'DCS SERVER CABINET SYSTEM 1',
            'DCS SERVER CABINET SYSTEM 3',
            'GENERATOR TRANSFORMER UNIT ENERGY METER PANEL',
            'GENERATOR GAS LEAKAGE DETECTION PROCESSOR PANEL',
            'DCS CABINET FOR ESP SYSTEM',
            '[E] DCS CABINET FOR ESP SYSTEM',
            'HVAC PLC PANEL FOR CENTRAL CONTROL BUILDING',
            'TV CONTROL PANEL FOR FURNACE AND DRUM',
            "  control\u{00A0}cabinet  ",
        ]);
    }

    #[DataProvider('newFamilies')]
    public function test_additional_families_require_explicit_whole_equipment_names(string $description, string $family): void
    {
        $asset = ['description' => $description, 'hierarchy_category' => 'equipment'];
        $before = $asset;
        $result = app(AssetIllustration::class)->forAsset($asset);
        $this->assertSame($family, $result['family']);
        $this->assertSame('GENERIC_AI_ILLUSTRATION', $result['kind']);
        $this->assertSame('NOT_ENGINEER_VERIFIED', $result['review_status']);
        $this->assertSame('/images/asset-families/'.$family.'-illustration-v1.png', $result['path']);
        $this->assertFileExists(public_path(ltrim($result['path'], '/')));
        $this->assertSame($before, $asset);
    }

    public static function newFamilies(): array
    {
        return [
            ['RAW WATER PUMP A', 'water-pump'],
            ['SCREEN WASH PUMP B', 'water-pump'],
            ['SCREEN WASH PUMP A (KSB)', 'water-pump'],
            ['SCREEN WASH PUMP C (KSB)', 'water-pump'],
            ['POTABLE WATER BOOSTER PUMP A', 'water-pump'],
            ['MAKE UP BOOSTER PUMP B', 'water-pump'],
            ['CLOSED CYCLE COOLING WATER PUMP A', 'water-pump'],
            ['CONDENSATE TRANSFER PUMP B', 'water-pump'],
            ['ASH CONTAINING WATER BOOSTER PUMP A', 'water-pump'],
            ['[E] RAW WATER PUMP B', 'water-pump'],
            ['BELT CONVEYOR 3', 'belt-conveyor'],
            ['BELT CONVEYOR (BC) 59', 'belt-conveyor'],
            ['[E] BELT CONVEYOR (BC) 48', 'belt-conveyor'],
            ['FOAM CONCENTRATE STORAGE TANK', 'storage-tank'],
            ['CONDENSATE STORAGE TANK', 'storage-tank'],
            ['DEMINERALIZED WATER TANK A', 'storage-tank'],
            ['POTABLE WATER TANK', 'storage-tank'],
            ['RAW WATER TANK', 'storage-tank'],
            ['FUEL OIL TANK', 'storage-tank'],
            ['[E] FOAM CONCENTRATE STORAGE TANK', 'storage-tank'],
        ];
    }

    #[DataProvider('thirdBatchFamilies')]
    public function test_more_families_match_only_the_intended_whole_equipment(string $description, string $family): void
    {
        $asset = ['description' => $description, 'hierarchy_category' => 'equipment'];
        $before = $asset;
        $result = app(AssetIllustration::class)->forAsset($asset);
        $this->assertSame($family, $result['family']);
        $this->assertSame('GENERIC_AI_ILLUSTRATION', $result['kind']);
        $this->assertSame('NOT_ENGINEER_VERIFIED', $result['review_status']);
        $this->assertSame('/images/asset-families/'.$family.'-illustration-v1.png', $result['path']);
        $this->assertFileExists(public_path(ltrim($result['path'], '/')));
        $this->assertSame($before, $asset);
    }

    public static function thirdBatchFamilies(): array
    {
        return [
            ['BOILER TRANSFORMER A', 'power-transformer'],
            ['MAINTENANCE TRANSFORMER', 'power-transformer'],
            ['TURBINE TRANSFORMER B', 'power-transformer'],
            ['WATER SYSTEM TRANSFORMER A', 'power-transformer'],
            ['STATION SERVICE TRANSFORMER B', 'power-transformer'],
            ['LIGHTING TRANSFORMER', 'power-transformer'],
            ['COAL HANDLING TRANSFORMER B', 'power-transformer'],
            ['ASH HANDLING TRANSFORMER A', 'power-transformer'],
            ['GENERATOR TRANSFORMER (GT) 730 MVA 525/20 KV', 'power-transformer'],
            ['STARTUP/STANDBY AUXILIARY TRANSFORMER (S/SAT) 45MVA 150/6KV', 'power-transformer'],
            ['UNIT AUXILIARY TRANSFORMER (UAT) A 34MVA 20/6KV', 'power-transformer'],
            ['[E] UNIT AUXILIARY TRANSFORMER (UAT) B 34MVA 20/6KV', 'power-transformer'],
            ['PRIMARY AIR FAN A', 'industrial-fan'],
            ['INDUCED DRAFT FAN B', 'industrial-fan'],
            ['FORCED DRAFT FAN A', 'industrial-fan'],
            ['SEALING AIR FAN B', 'industrial-fan'],
            ['FLAME MONITORS COOLING AIR FAN A', 'industrial-fan'],
            ['FORCED DRAFT FAN OF START UP BOILER', 'industrial-fan'],
            ['[E] INDUCED DRAFT FAN B', 'industrial-fan'],
            ['OIL FREE SCREW TYPE AIR COMPRESSOR A', 'screw-air-compressor'],
            ['OIL FREE SCREW TYPE AIR COMPRESSOR D', 'screw-air-compressor'],
            ['PULVERIZER (MILL) A', 'coal-pulverizer'],
            ['PULVERIZER (MILL) G', 'coal-pulverizer'],
            ['[E] PULVERIZER (MILL) F', 'coal-pulverizer'],
            ['ELECTRIC HOIST TURBINE AREA', 'electric-hoist'],
            ['ELECTRIC HOIST BOILER AREA', 'electric-hoist'],
            ['ELECTRIC HOIST COAL-ASH AREA', 'electric-hoist'],
            ['[E] ELECTRIC HOIST AUXILIARY PLANT AREA', 'electric-hoist'],
        ];
    }

    #[DataProvider('fourthBatchFamilies')]
    public function test_handling_and_air_service_families_keep_their_exact_subject(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
    }

    public static function fourthBatchFamilies(): array
    {
        return [
            ['COAL FEEDER A', 'coal-feeder'],
            ['[E] COAL FEEDER G', 'coal-feeder'],
            ['BELT FEEDER (BF) 52', 'belt-feeder'],
            ['BELT FEEDER (BF) 53', 'belt-feeder'],
            ['BELT FEEDER 59', 'belt-feeder'],
            ['BELT FEEDER C (JH 8 D)', 'belt-feeder'],
            ['BELT FEEDER D (JH 8 D)', 'belt-feeder'],
            ['VIBRATING FEEDER 81', 'vibrating-feeder'],
            ['VIBRATING FEEDER 84', 'vibrating-feeder'],
            ['COAL CRUSHER C', 'coal-crusher'],
            ['COAL CRUSHER D', 'coal-crusher'],
            ['CCCW HEAT EXCHANGER A', 'heat-exchanger'],
            ['[E] CCCW HEAT EXCHANGER B', 'heat-exchanger'],
            ['AIR PREHEATER A', 'air-preheater'],
            ['AIR PREHEATER B', 'air-preheater'],
            ['DESICANT AIR DRYER A', 'desiccant-air-dryer'],
            ['DESICANT AIR DRYER C', 'desiccant-air-dryer'],
            ['INSTRUMENT AIR RECEIVER TANK', 'air-receiver'],
            ['SERVICE AIR RECEIVER TANK', 'air-receiver'],
            ['TRAVELLING SCREEN A', 'travelling-screen'],
            ['[E] TRAVELLING SCREEN C', 'travelling-screen'],
        ];
    }

    #[DataProvider('fifthBatchFamilies')]
    public function test_pump_service_allowlists_do_not_change_source_identity(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
        $this->test_additional_families_require_explicit_whole_equipment_names('[E] '.strtolower($description), $family);
        foreach (['MOTOR '.$description, $description.' & OTHER PUMP', 'FAN FOR '.$description] as $ambiguous) {
            $result = app(AssetIllustration::class)->forAsset([
                'description' => $ambiguous,
                'hierarchy_category' => 'equipment',
            ]);
            if ($ambiguous === 'MOTOR TURBINE BEARING OIL PUMP') {
                // This separately audited whole motor now has its own image.
                $this->assertSame('electric-machine', $result['family']);
                $this->assertNotSame($family, $result['family']);
            } else {
                $this->assertNull($result);
            }
        }
    }

    public static function fifthBatchFamilies(): array
    {
        return [
            ['VACUUM PUMP A', 'vacuum-pump'],
            ['VACUUM PUMP C', 'vacuum-pump'],
            ['CONDENSER WATERBOX VACUUM PRIMING PUMP', 'vacuum-pump'],
            ['FUEL OIL PUMP A', 'oil-pump'],
            ['FUEL OIL PUMP C', 'oil-pump'],
            ['LIGHT OIL TRANSFER PUMP B', 'oil-pump'],
            ['DC TURBINE EMERGENCY OIL PUMP', 'oil-pump'],
            ['SEAL OIL BACK UP PUMP', 'oil-pump'],
            ['TURBINE BEARING OIL PUMP', 'oil-pump'],
            ['CIRCULATING WATER PUMP A', 'circulating-water-pump'],
            ['CIRCULATING WATER PUMP C', 'circulating-water-pump'],
            ['CONDENSATE EXTRACTION PUMP A', 'condensate-extraction-pump'],
            ['CONDENSATE EXTRACTION PUMP B', 'condensate-extraction-pump'],
            ['BOILER CIRCULATING PUMP (6KV) BCP A', 'boiler-circulating-pump'],
            ['BOILER CIRCULATING PUMP (6KV) BCP C', 'boiler-circulating-pump'],
            ['BOOSTER PUMP OF TURBINE DRIVEN FEED PUMP A', 'feedwater-booster-pump'],
            ['BOOSTER PUMP OF TURBINE DRIVEN FEED PUMP B', 'feedwater-booster-pump'],
            ['DEMINERALIZED WATER BOOSTER PUMP A', 'water-pump'],
            ['DISTILLATE PUMP B', 'water-pump'],
            ['DISTILLATE INJECTION PUMP A', 'water-pump'],
            ['BRINE BLOW DOWN PUMP B', 'water-pump'],
            ['SEAWATER BOOSTER PUMP A OF CHLORINE PLANT', 'water-pump'],
            ['SEA WATER INTAKE PUMP A (DESAL SUPPLY PUMP A)', 'water-pump'],
            ['SEA WATER INTAKE PUMP B (DESAL SUPPLY PUMP B)', 'water-pump'],
            ['BACKWASHING PUMP B OF CPP REGENERATION', 'water-pump'],
            ['SERVICE WATER TRANSFER PUMP TO JH 8A (AREA COAL HANDLING)', 'water-pump'],
            ['SHUTDOWN COOLING WATER PUMP', 'water-pump'],
        ];
    }

    #[DataProvider('sixthBatchFamilies')]
    public function test_material_flow_and_thermal_equipment_keep_exact_subjects(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
        $this->test_additional_families_require_explicit_whole_equipment_names('[E] '.strtolower($description), $family);
        foreach (['MOTOR '.$description, $description.' & OTHER EQUIPMENT', 'FAN FOR '.$description] as $ambiguous) {
            $this->assertNull(app(AssetIllustration::class)->forAsset([
                'description' => $ambiguous,
                'hierarchy_category' => 'equipment',
            ]));
        }
    }

    public static function sixthBatchFamilies(): array
    {
        return [
            ['DIVERTER GATE (DG) 55/C', 'diverter-gate'],
            ['DIVERTER GATE (DG) 56/D', 'diverter-gate'],
            ['DIVERTER GATE 1', 'diverter-gate'],
            ['DIVERTER GATE 43', 'diverter-gate'],
            ['DIVERTER GATE 90', 'diverter-gate'],
            ['DIVERTER GATE 54 (INLET HOPPER JH 8D)', 'diverter-gate'],
            ['DIVERTER GATE BC 03 JH 8A', 'diverter-gate'],
            ['DIVERTER GATE BC 04 STRE', 'diverter-gate'],
            ['AUXILIARY STEAM DRAIN FLASH TANK', 'flash-vessel'],
            ['BLOW-OFF FLASH VESSEL TANK', 'flash-vessel'],
            ['CONTINOUS BLOWDOWN TANK', 'flash-vessel'],
            ['INTERMITTENT BLOWDOWN FLASH TANK', 'flash-vessel'],
            ['FLASH TANK A (26 M3)', 'flash-vessel'],
            ['FLASH TANK B (13 M3)', 'flash-vessel'],
            ['ASH CONTAINING WATER AERATION BLOWER A', 'industrial-blower'],
            ['ESP HOPPER AERATION BLOWER B', 'industrial-blower'],
            ['ROOTS BLOWER A OF CPP REGENERATION', 'industrial-blower'],
            ['HP HEATER 1', 'feedwater-heater'],
            ['HP HEATER 3', 'feedwater-heater'],
            ['LP HEATER 5', 'feedwater-heater'],
            ['LP HEATER 6', 'feedwater-heater'],
            ['LP HEATER 7A', 'feedwater-heater'],
            ['LP HEATER 7B', 'feedwater-heater'],
            ['LP HEATER 8A', 'feedwater-heater'],
            ['LP HEATER 8B', 'feedwater-heater'],
        ];
    }

    #[DataProvider('seventhBatchFamilies')]
    public function test_waste_dosing_and_fire_pumps_keep_whole_equipment_subjects(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
        $this->test_additional_families_require_explicit_whole_equipment_names('[E] '.strtolower($description), $family);
        foreach (['MOTOR '.$description, 'DOOR '.$description, $description.' & OTHER EQUIPMENT', 'FAN FOR '.$description] as $ambiguous) {
            $this->assertNull(app(AssetIllustration::class)->forAsset([
                'description' => $ambiguous,
                'hierarchy_category' => 'equipment',
            ]));
        }
    }

    public static function seventhBatchFamilies(): array
    {
        return [
            ['ASH CONTAINING WATER LIFT PUMP A', 'sludge-pump'],
            ['ASH CONTAINING WATER SLUDGE PUMP B', 'sludge-pump'],
            ['ASH CONTAINING WATER VACUUM CAN LIFT PUMP A', 'sludge-pump'],
            ['ASH CONTAINING WATER VACUUM CAN SLUDGE PUMP B', 'sludge-pump'],
            ['DEHYDRATOR SLUDGE SUPPLY PUMP A', 'sludge-pump'],
            ['MIXED REGENERATIVE WASTEWATER PUMP A', 'wastewater-pump'],
            ['MIXED REGENERATIVE WASTEWATER PUMP B', 'wastewater-pump'],
            ['WASTE WATER PUMP A USED FOR CPP REGENERATION', 'wastewater-pump'],
            ['WASTE WATER PUMP B USED FOR CPP REGENERATION', 'wastewater-pump'],
            ['WASTE WATER PUMP FOR STORAGE POND WWTP', 'wastewater-pump'],
            ['UNDERWATER PUMP OF WWTP SYSTEM (LINGKUNGAN)', 'wastewater-pump'],
            ['UNIT DRAINAGE PIT DISCHARGE PUMP A', 'wastewater-pump'],
            ['UNIT DRAINAGE PIT DISCHARGE PUMP B', 'wastewater-pump'],
            ['CONTINUOUS DOSING PUMP A', 'dosing-pump'],
            ['CONTINUOUS DOSING PUMP B', 'dosing-pump'],
            ['IMPACT DOSING PUMP', 'dosing-pump'],
            ['FRESH WATER DIESEL DRIVEN FIRE FIGHTING PUMP', 'diesel-fire-pump'],
            ['SEAWATER DIESEL DRIVEN FIRE FIGHTING PUMP', 'diesel-fire-pump'],
            ['FRESH WATER MOTOR DRIVEN FIRE FIGHTING PUMP', 'electric-fire-pump'],
            ['JOCKEY PUMP A', 'jockey-pump'],
            ['JOCKEY PUMP B', 'jockey-pump'],
        ];
    }

    #[DataProvider('instrumentationDescriptions')]
    public function test_instrumentation_subjects_never_use_the_parent_machine_image(string $description): void
    {
        $result = app(AssetIllustration::class)->forAsset(['description' => $description, 'hierarchy_category' => 'equipment']);
        $this->assertSame('instrumentation-kit', $result['family']);
        $this->assertSame('equipment', $result['subject_level']);
    }

    public static function instrumentationDescriptions(): array
    {
        return [
            ['RAW WATER PUMP A INSTRUMENTATION DEVICES'],
            ['BELT CONVEYOR (BC) 48 INSTRUMENTATION DEVICES'],
            ['BOILER TRANSFORMER A INSTRUMENTATION DEVICES'],
            ['PRIMARY AIR FAN A INSTRUMENTATION DEVICES'],
            ['AIR COMPRESSOR A INSTRUMENTATION DEVICES'],
            ['PULVERIZER (MILL) & COAL FEEDER A INSTRUMENTATION DEVICES'],
            ['COAL FEEDER A INSTRUMENTATION DEVICES'],
            ['COAL CRUSHER C INSTRUMENTATION DEVICES'],
            ['SCREEN WASH PUMP A (KSB) INSTRUMENTATION DEVICES'],
            ['CHLORINE PLANT INSTRUMENTATION DEVICES'],
            ['CONDENSATE POLISHING PLANT INSTRUMENTATION DEVICE'],
            ['[E] PULVERIZER (MILL) & COAL FEEDER A INSTRUMENTATION DEVICES'],
        ];
    }

    public function test_generic_family_rules_do_not_guess_machine_or_part_from_context(): void
    {
        $service = app(AssetIllustration::class);
        foreach (['INSTRUMENTATION DEVICES', 'RAW WATER PUMP A INSTRUMENTATION DEVICES HOUSING', 'RAW WATER PUMP A INSTRUMENTATION DEVICES PART', 'FAN FOR INSTRUMENTATION DEVICES', 'EH PUMP A FOR UNKNOWN', 'MOTOR EH PUMP A FOR TURBINE', 'RECYCLING PUMP MOTOR'] as $name) {
            $this->assertNull($service->forAsset(['description' => $name, 'hierarchy_category' => 'equipment']));
        }
        $this->assertSame('air-receiver', $service->forAsset(['description' => 'INSTRUMENT AIR RECEIVER TANK', 'hierarchy_category' => 'equipment'])['family']);
        $this->assertSame('control-cabinet', $service->forAsset(['description' => 'INSTRUMENT PANEL POWER SUPPLY CABINET', 'hierarchy_category' => 'equipment'])['family']);
        foreach (['EH PUMP A FOR BFPT', 'EH PUMP B FOR TURBINE', 'RECYCLING PUMP', 'REGENERATION SPECIAL PUMP A'] as $name) {
            $result = $service->forAsset(['description' => $name, 'hierarchy_category' => 'equipment']);
            $this->assertSame('water-pump', $result['family']);
            $this->assertSame('Pompa', $result['label']);
        }
    }

    #[DataProvider('partDescriptions')]
    public function test_parts_use_their_own_subject_not_the_named_parent_machine(string $description, string $family): void
    {
        $service = app(AssetIllustration::class);
        $asset = ['description' => $description, 'hierarchy_category' => 'part'];
        $before = $asset;
        $result = $service->forAsset($asset);
        $this->assertSame($family, $result['family']);
        $this->assertSame('part', $result['subject_level']);
        $this->assertSame('GENERIC_AI_ILLUSTRATION', $result['kind']);
        $this->assertSame('NOT_ENGINEER_VERIFIED', $result['review_status']);
        $this->assertSame($before, $asset);
        $normalized = str_replace(' ', "\u{00A0}", strtolower($description));
        $this->assertSame($family, $service->forAsset(['description' => $normalized, 'hierarchy_category' => 'part'])['family']);
        foreach (['equipment', 'component', 'system', 'unknown', null] as $category) {
            $this->assertNull($service->forAsset(['description' => $description, 'hierarchy_category' => $category]));
        }
        foreach (['DOOR OF '.$description, 'MOTOR FOR '.$description, $description.' HOUSING', $description.' & OTHER PARTS', $description.' FOR UNKNOWN'] as $ambiguous) {
            $this->assertNull($service->forAsset(['description' => $ambiguous, 'hierarchy_category' => 'part']));
        }
    }

    public static function partDescriptions(): array
    {
        return [
            ['TDBFP A BP MOTOR WINDING TEMPERATURE RTD1', 'part-temperature-sensor'],
            ['TDBFP B BP MOTOR BEARING TEMPERATURE RTD 6', 'part-temperature-sensor'],
            ['TDBFP A THURST BEARING TEMPERATURE RTD2', 'part-temperature-sensor'],
            ['TDBFP B MECHANICAL SEAL WATER INLET TEMPERATURE RTD 1', 'part-temperature-sensor'],
            ['BFPT A LUBE OIL FILTER INLET TEMPERATURE THERMOCOUPLE', 'part-temperature-sensor'],
            ['BFPT B LUBE OIL TANK TEMPERATURE THERMOCOUPLE', 'part-temperature-sensor'],
            ['BFPT A JACKING OIL PUMP B OUTLET PRESSURE GAUGE', 'part-dial-gauge'],
            ['BFPT B NO.1 MOP OUTLET PRESSSURE GAUGE', 'part-dial-gauge'],
            ['BFPT A NO. 2 BEARING INLET OIL PRESSURE GAUGE', 'part-dial-gauge'],
            ['BFPT B BEARING OIL RETURN TEMPERATURE (BACKWARD) THERMOMETER', 'part-dial-gauge'],
            ['TDBFP A NO. 3 BEARING OIL RETURN TEMPERATURE THERMOMETER', 'part-dial-gauge'],
            ['BFPT A CONTROL OIL STRAINER DIFFERENTIAL PRESSURE SWITCH', 'part-industrial-switch'],
            ['BFPT B LUBE OIL PRESSURE SWITCH LL (3)', 'part-industrial-switch'],
            ['BFPT A LUBE OIL TANK LEVEL SWITCH', 'part-industrial-switch'],
            ['BFPT B LUBE OIL PRESSURE SWITCH LLL', 'part-industrial-switch'],
            ['BFPT A GLAND SEAL STEAM PRESSURE TRANSMITTER', 'part-transmitter'],
            ['BFPT B INLET PRESSURE TRANSMITTER', 'part-transmitter'],
            ['ES 4 TO BFPT STEAM FLOW TRANSMITTER', 'part-transmitter'],
            ['MOTOR CONTROL VALVE COLD PRIMARY AIR DAMPER TO MILL A', 'part-valve-damper'],
            ['MOTOR CONTROL VALVE HOT PRIMARY AIR DAMPER TO MILL B', 'part-valve-damper'],
            ['PNEUMATIC OPERATE VALVE HOT PRIMARY AIR TO MILL A', 'part-valve-damper'],
            ['SEAL AIR PIPING PULVERIZER (MILL) A', 'part-piping'],
            ['SEAL AIR PIPING PULVERIZER (MILL) B', 'part-piping'],
        ];
    }

    public function test_unknown_parts_and_category_prefixes_do_not_invent_classification(): void
    {
        foreach (['PUMP A', '[P] TDBFP A BP MOTOR WINDING TEMPERATURE RTD1', 'TDBFP C BP MOTOR WINDING TEMPERATURE RTD1', 'TDBFP A BP MOTOR WINDING TEMPERATURE RTD7', 'BFPT B GLAND SEAL STEAM PRESSURE TRANSMITTER', 'PNEUMATIC OPERATE VALVE HOT PRIMARY AIR TO MILL B', 'BFPT A LUBE OIL PRESSURE SWITCH LL (4)', 'SEAL AIR PIPING PULVERIZER (MILL) C', 'UNKNOWN PRESSURE GAUGE'] as $name) {
            $this->assertNull(app(AssetIllustration::class)->forAsset(['description' => $name, 'hierarchy_category' => 'part']));
        }
    }

    #[DataProvider('partFamilies')]
    public function test_part_details_render_labeled_part_media_without_extra_requests(string $description, string $family, string $label): void
    {
        $this->test_asset_detail_labels_the_illustration_without_new_requests_or_source_writes($description, $family, $label, 'part');
    }

    public static function partFamilies(): array
    {
        return [
            ['TDBFP A BP MOTOR WINDING TEMPERATURE RTD1', 'part-temperature-sensor', 'Sensor suhu (Part)'],
            ['BFPT A ACCUMULATOR PRESSURE GAUGE', 'part-dial-gauge', 'Gauge / thermometer (Part)'],
            ['BFPT A LUBE OIL TANK LEVEL SWITCH', 'part-industrial-switch', 'Process switch (Part)'],
            ['BFPT A INLET PRESSURE TRANSMITTER', 'part-transmitter', 'Transmitter (Part)'],
            ['MOTOR CONTROL VALVE HOT PRIMARY AIR DAMPER TO MILL A', 'part-valve-damper', 'Valve / damper / gate (Part)'],
            ['SEAL AIR PIPING PULVERIZER (MILL) A', 'part-piping', 'Perpipaan (Part)'],
        ];
    }

    #[DataProvider('genericObjectFamilies')]
    public function test_generic_object_reuse_keeps_source_level_and_subject(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
        $this->test_additional_families_require_explicit_whole_equipment_names('[E] '.strtolower($description), $family);
        $this->test_additional_families_require_explicit_whole_equipment_names(str_replace(' ', "\u{00A0}", $description), $family);
        $service = app(AssetIllustration::class);
        $result = $service->forAsset(['description' => $description, 'hierarchy_category' => 'equipment']);
        $this->assertSame('equipment', $result['subject_level']);
        $this->assertStringNotContainsString('(Part)', $result['label']);
        foreach (['DOOR OF '.$description, 'FAN FOR '.$description, 'SPARE '.$description, 'CABLE '.$description, 'FOUNDATION '.$description, 'REPAIR '.$description, $description.' MOTOR', $description.' HOUSING', $description.' & OTHER ITEMS', $description.' FOR UNKNOWN'] as $ambiguous) {
            $this->assertNull($service->forAsset(['description' => $ambiguous, 'hierarchy_category' => 'equipment']));
        }
        foreach (['part', 'component', 'system', 'unknown'] as $category) {
            $this->assertNull($service->forAsset(['description' => $description, 'hierarchy_category' => $category]));
        }
    }

    public static function genericObjectFamilies(): array
    {
        return [
            ['AIR HANDLING UNIT CCB AREA', 'hvac-unit'],
            ['AIR HANDLING UNIT COMPRESSOR ROOM AREA', 'hvac-unit'],
            ['AIR-COOLED LIQUID CHILLER', 'hvac-unit'],
            ['ACID METERING SET FOR MIXED BED', 'chemical-dosing-kit'],
            ['ALKALI METERING SET FOR MIXED BED WTP', 'chemical-dosing-kit'],
            ['DEHYDRANT METERING SET FOR WWTP', 'chemical-dosing-kit'],
            ['ALKALI DOSING EQUIPMENT SET OF CPP (INCLUDE TANK & PUMP)', 'chemical-dosing-kit'],
            ['SODIUM BI SULPHITE DOSING EQUIPMENT SET', 'chemical-dosing-kit'],
            ['LIME DOSING EQUIPMENT SET POTABLE WATER SYSTEM', 'chemical-dosing-kit'],
            ['SODIUM HYPOCHLORIT SET FOR WWTP', 'chemical-dosing-kit'],
            ['ANTISCALANT SET FOR ASH CONTAINING WATER', 'chemical-dosing-kit'],
            ['HYDRAZINE SUPPLY AND DISTRIBUTION EQUIPMENT', 'chemical-dosing-kit'],
            ['HYDROGEN (H2) PLANT (FRAME I)', 'chemical-dosing-kit'],
            ['SODIUM HYPOCHLORITE GENERATOR SET', 'chemical-dosing-kit'],
            ['ACID CLEANING SET EQUIPMENTS OF CHLORINE PLANT', 'chemical-dosing-kit'],
            ['MAKE UP PURE WATER AND ALKALINE SOLUTION SKID H2 PLANT', 'chemical-dosing-kit'],
            ['EH OIL FOR BFPT PURIFICATION SYSTEM', 'chemical-dosing-kit'],
            ['GENERATOR STATOR COOLING WATER SYSTEM', 'chemical-dosing-kit'],
            ['HYDRAULIC SYSTEM FOR STRE', 'chemical-dosing-kit'],
            ['TURBINE LUBE OIL SYSTEM', 'chemical-dosing-kit'],
            ['CWP SEALING SYSTEM', 'chemical-dosing-kit'],
            ['CONDENSATE DESUPERHEATING SPRAY SYSTEM', 'chemical-dosing-kit'],
            ['ASH CONTAINING WATER PURIFYING SET B', 'chemical-dosing-kit'],
            ['CLARIFIER OF WWTP', 'chemical-dosing-kit'],
            ['DEHYDRATOR INCLUDE SLUDGE HOPPER OF WWTP', 'chemical-dosing-kit'],
            ['FILTRASI & TANK HSD ALBES', 'chemical-dosing-kit'],
            ['MULTI EFFECT DESALINATION (MED) A', 'chemical-dosing-kit'],
            ['OIL WATER SEPARATOR', 'chemical-dosing-kit'],
            ['SEWAGE TREATMENT EQUIPMENT SET', 'chemical-dosing-kit'],
            ['DELUGE & SPRINKLER SYSTEM AREA TURBINE & TRAFO', 'fire-protection-kit'],
            ['HYDRANT/HOSEREEL AREA ASH HANDLING & COAL HANDLING', 'fire-protection-kit'],
            ['DRENCHER SPRINKLER/COOLING FIRE FIGHTING SYSTEM FUEL OIL TANK', 'fire-protection-kit'],
            ['LP CO2 SUPRESSION EQUIPMENT', 'fire-protection-kit'],
            ['FIRE ALARM SYSTEM AREA BOP', 'fire-protection-kit'],
            ['DUST SUPRESSION SYSTEM JUNCTION HOUSE 8D', 'dust-spray-kit'],
            ['SPRAY WATER SYSTEM FOR STRE', 'dust-spray-kit'],
            ['MOTOR TURBINE BEARING OIL PUMP', 'electric-machine'],
            ['GENERATOR QFSN-625-2 625MW 20KV 21227A', 'electric-machine'],
            ['EMERGENCY DIESEL GENERATOR (EDG) 1020KW 400V 50HZ', 'electric-machine'],
            ['110V BATTERY BANK A (600AH)', 'battery-bank'],
            ['110V BATTERY BANK COAL HANDLING (100AH)', 'battery-bank'],
            ['220V BATTERY BANK (2000AH)', 'battery-bank'],
            ['220V BATTERY BANK FOR MAIN UPS (580AH)', 'battery-bank'],
            ['TURBINE TURNING GEAR', 'gear-assembly'],
            ['AC NON-SEGREGATED PHASE BUSDUCT (NPB) TO EXCT', 'busduct'],
            ['DC NON-SEGREGATED PHASE BUSDUCT (NPB) FROM EXCT', 'busduct'],
            ['ISOLATED PHASE BUS (IPB) 24KV 24000A', 'busduct'],
            ['NON-SEGREGATED PHASE BUS (NPB) FROM S/SAT', 'busduct'],
            ['NON-SEGREGATED PHASE BUS (NPB) FROM UAT B', 'busduct'],
            ['150KV LIGHTNING ARRESTER (LA)', 'lightning-arrester'],
            ['COMPRESSOR BUILDING & ESP PROPER BUILDING', 'industrial-building'],
            ['STRUCTURES OF CENTRAL CONTROL BUILDING (CCB) & TURBINE HOUSE', 'industrial-building'],
            ['WORKSHOP FACILITY BUILDING', 'industrial-building'],
            ['HANGER STRUCTURES OF BOILER HOUSE', 'structural-support'],
            ['STRUCTURE OF TURBINE-GENERATOR FOUNDATION', 'structural-support'],
            ['COAL YARD 2', 'industrial-site'],
            ['ROAD WAY', 'industrial-site'],
            ['DINDING BUKIT', 'industrial-site'],
            ['SETTLING BASIN PULVERIZER (MILL)', 'water-basin'],
            ['UNIT DRAINAGE PIT', 'water-basin'],
            ['WASTE WATER PIT OF CPP REGENERATION', 'water-basin'],
            ['CHIMNEY (STACK)', 'industrial-chimney'],
            ['OUTDOOR LIGHTING COAL HANDLING AREA', 'outdoor-lighting'],
            ['MICRO OIL BURNER', 'industrial-burner'],
            ['STARTUP BOILER IGNITOR AND BURNER', 'industrial-burner'],
            ['OIL GUN LAYER FG', 'industrial-burner'],
            ['COAL SAMPLER UNIT JH8D', 'coal-sampler'],
            ['DRY ASH UNLOADER', 'dry-ash-unloader'],
            ['ELECTROSTATIC PRECIPITATOR B CHAMBER COLLECTING/EMITING RAPPER', 'rapper-mechanism'],
            ['MAGNETIC SEPARATOR 81 (81A & 81B)', 'magnetic-separator'],
            ['MAGNETIC SEPARATOR FOR BC 4 STRE', 'magnetic-separator'],
            ['STRE CABLE CHAIN SYSTEM 10.5 KV', 'cable-chain'],
            ['AUTOMATIC GENERATION CONTROL (AGC) SYSTEM', 'instrumentation-kit'],
            ['CONTINUOUS EMISION MONITORING SYSTEM (CEMS)', 'instrumentation-kit'],
            ['DEH SYSTEM', 'instrumentation-kit'],
            ['CCTV SYSTEM', 'instrumentation-kit'],
            ['INDUCED DRAFT FAN FAULT DIAGNOSIS', 'instrumentation-kit'],
            ['PARTIAL DISCHAGRE ONLINE MONITORING', 'instrumentation-kit'],
            ['GENERATOR HYDROGEN (H2) PURITY MONITORING CIRCUIT', 'instrumentation-kit'],
            ['GATE AND HEADSTOCK GEAR', 'part-valve-damper'],
            ['TRASH RACK SYSTEM', 'travelling-screen'],
            ['ELEVATOR', 'industrial-elevator'],
            ['RESIN HANDLING BARROW', 'utility-barrow'],
            ['SOLAR PANEL', 'solar-panel'],
            ['TELEPHONE CCR', 'desk-telephone'],
            ['WIND TURBINE', 'wind-turbine'],
            ['BOILER TUBES OF START UP BOILER', 'part-piping'],
            ['ECONOMIZER TUBES', 'part-piping'],
            ['REHEATER TUBES', 'part-piping'],
            ['SUPERHEATER TUBES', 'part-piping'],
            ['WALL / FURNACE TUBES', 'part-piping'],
            ['GENERATOR H2 SUPPLY MANIFOLD (FROM H2 GAS VESSEL/CYLINDER)', 'part-piping'],
            ['HYDROGEN MANIFOLD FOR GENERATOR COOLING', 'part-piping'],
            ['FLUE GAS DUCTING AND DAMPER', 'part-piping'],
            ['HVAC DUCTING & DAMPER', 'part-piping'],
            ['PRIMARY AIR DUCTING & DAMPER', 'part-piping'],
            ['SECONDARY AIR DUCTING & DAMPER', 'part-piping'],
            ['CCOFA & SOFA DAMPER', 'part-valve-damper'],
            ['SECONDARY AIR DAMPER COAL LAYER D, DE & E', 'part-valve-damper'],
            ['SECONDARY AIR DAMPER LAYER AA, A & AB', 'part-valve-damper'],
            ['SECONDARY AIR DAMPER LAYER G & GG', 'part-valve-damper'],
            ['ANALYZER OF SAMPLING RACK SYSTEM', 'instrumentation-kit'],
            ['H2 PURITY ANALYZER BOX', 'instrumentation-kit'],
            ['GAS LEAKAGE DETECTOR', 'instrumentation-kit'],
            ['METAL DETECTOR B', 'instrumentation-kit'],
            ['WATER/COAL/OIL QUALITY INSTRUMENT', 'instrumentation-kit'],
            ['PLC ASH HANDLING SYSTEM', 'control-cabinet'],
            ['PLC FOR STRE', 'control-cabinet'],
            ['PLC HYDROGEN (H2) PLANT', 'control-cabinet'],
            ['150KV PACKAGE GIS', 'control-cabinet'],
            ['UPS UNIT', 'control-cabinet'],
            ['CATHODIC PROTECTION RECTIFIER FOR CWP PIPE', 'control-cabinet'],
            ['CATHODIC PROTECTION RECTIFIER FOR CWP PUMP A', 'control-cabinet'],
            ['ESP A TRANSFORMER-RECTIFIER FIELD 1', 'power-transformer'],
            ['ESP B TRANSFORMER-RECTIFIER FIELD 4', 'power-transformer'],
            ['HIGH FLOW RATE MIXED BED C OF CPP SYSTEM', 'process-filter'],
            ['MIXED BED B', 'process-filter'],
            ['COMPRESS AIR TANK A,B & C', 'air-receiver'],
            ['NEUTRALIZATION, REACTION,FLOCCULATION TANK & AGITATOR OF WWTP', 'air-receiver'],
            ['SLUDGE ENRICHMENT TANK INCLUDE AGITATOR', 'air-receiver'],
            ['RESIN HOPPER (INCLUDE EJECTOR) OF CPP REGENERATION', 'storage-tank'],
            ['ROOTS FAN A, B, PIPING & AERATOR', 'industrial-blower'],
            ['PIPING & VALVE FOR DOSING MED', 'part-piping'],
            ['PIPING & VALVE OF CHEMICALS SUPPLY (DOSING) FOR CONDENSATE POLISHING PLANT', 'part-piping'],
            ['PIPING & VALVES OF EH OIL SYSTEM FOR BFPT', 'part-piping'],
            ['PIPING, VALVES & ASSESORIES FOR FOAM SYSTEM', 'part-piping'],
            ['INSTRUMENT AIR DISTRIBUTION PIPING & VALVE UNIT', 'part-piping'],
            ['HP BYPASS PIPING AND VALVE OF MAIN STEAM', 'part-piping'],
            ['LP BYPASS PIPING & VALVE B OF REHEAT STEAM', 'part-piping'],
            ['START UP BOILER PIPING & VALVE OF STEAM', 'part-piping'],
            ['DOSING PIPING FOR DEMINERALIZATION PLANT', 'part-piping'],
            ['COAL PIPE G', 'part-piping'],
            ['BOILER POWER CENTER A', 'control-cabinet'],
            ['110V DC DISTRIBUTION BOARD NORMAL SYSTEM B', 'control-cabinet'],
            ['DC DISTRIBUTON BOARD NORMAL SYSTEM 220V', 'control-cabinet'],
            ['6 KV STATION SERVICE BOARD A', 'control-cabinet'],
            ['EMERGENCY AUXILIARY POWER BOARD B', 'control-cabinet'],
            ['LIGHTING BOARD', 'control-cabinet'],
            ['SWITCHGEAR 6 KV UNIT BOARD A', 'control-cabinet'],
            ['STRE SWITCHGEAR (RM 6) MEDIUM VOLTAGE', 'control-cabinet'],
            ['STRE MEDIUM VOLTAGE DISTRIBUTION PANEL 10.5 KV (JH 8 D)', 'control-cabinet'],
            ['COMMON HBT PANEL', 'control-cabinet'],
            ['CABINET OF H2 PLANT (RECTIFIER,MCC,CONTROL)', 'control-cabinet'],
            ['FOAM STORAGE TANK ROOM CONTROL BOX', 'control-cabinet'],
            ['COAL BUNKER A', 'storage-tank'],
            ['ESP HOPPER ROW 4', 'storage-tank'],
            ['UNDERGROUND HOPPER', 'storage-tank'],
            ['DRAG DRAIN CHAIN CONVEYOR 4', 'belt-conveyor'],
            ['BELT CONVEYOR 4 FOR STRE', 'belt-conveyor'],
            ['BOOM/ STACKING BELT CONVEYOR FOR STRE', 'belt-conveyor'],
            ['SECONDARY SCRAPPER CONVEYOR FOR STRE', 'belt-conveyor'],
            ['SSC (SUBMERGED SCRAPPER CONVEYOR)', 'belt-conveyor'],
            ['EH OIL TANK FOR TURBINE', 'air-receiver'],
            ['HYDROGEN STORAGE TANK (VESSEL) OF H2 PLANT', 'air-receiver'],
            ['ANION RESIN REGENERATION & SAMAEPARATION VESSEL', 'air-receiver'],
            ['DEAERATOR', 'air-receiver'],
            ['CONDENSER A', 'heat-exchanger'],
            ['GLAND STEAM CONDENSER', 'heat-exchanger'],
            ['STEAM HEATER OF PA TO PULVERIZER A', 'heat-exchanger'],
            ['ESP TRANSFORMER A', 'power-transformer'],
            ['EXCITATION TRANSFORMER 6900KVA 20/0.88KV SET', 'power-transformer'],
            ['STRE DRY TRANFORMER 10.5 KV/ 400 V 1 MVA', 'power-transformer'],
            ['ASH CRUSHER', 'coal-crusher'],
            ['GENERATOR HYDROGEN (H2) DRYER', 'desiccant-air-dryer'],
            ['TURBINE VALVE', 'part-valve-damper'],
            ['START UP BFP', 'water-pump'],
        ];
    }

    #[DataProvider('machineAndVehicleFamilies')]
    public function test_new_main_objects_do_not_borrow_context_machine_images(string $description, string $family): void
    {
        $this->test_additional_families_require_explicit_whole_equipment_names($description, $family);
        $this->test_additional_families_require_explicit_whole_equipment_names('[E] '.strtolower($description), $family);
        foreach (['DOOR OF '.$description, 'FAN FOR '.$description, $description.' MOTOR', $description.' PRESSURE GAUGE', $description.' & OTHER EQUIPMENT'] as $name) {
            $this->assertNull(app(AssetIllustration::class)->forAsset(['description' => $name, 'hierarchy_category' => 'equipment']));
        }
    }

    public static function machineAndVehicleFamilies(): array
    {
        return [
            ['AIR HEATER SOOTBLOWER', 'sootblower'],
            ['LONG RETRACTABLE SOOTBLOWER LEFT SIDE', 'sootblower'],
            ['SHORT RETRACTABLE SOOTBLOWER E', 'sootblower'],
            ['BOILER FEED PUMP TURBINE (BFPT) A', 'steam-turbine'],
            ['HIP TURBINE', 'steam-turbine'],
            ['LP 2 TURBINE', 'steam-turbine'],
            ['AUTOMATIC WASHING FILTER A OF CHLORINE PLANT', 'process-filter'],
            ['DEBRIS FILTER CW PIPE TO CONDENSER B', 'process-filter'],
            ['ELECTRIC FILTER OPEN COOLING WATER', 'process-filter'],
            ['SEAWATER PREFILTER OF CHLORINE PLANT', 'process-filter'],
            ['DUMP TRUCK (HINO) 04', 'truck'],
            ['FIRE TRUCK A (HOWO) (SAFETY)', 'truck'],
            ['FIRE TRUCK B (ZIEGLER TLF40/100-10)', 'truck'],
            ['VACUUM TRUCK', 'truck'],
            ['EXCAVATOR A (CATERPILLAR 320)', 'excavator'],
            ['EXCAVATOR B (VOLVO EC210B)', 'excavator'],
            ['FORKLIFT A', 'forklift'],
            ['FORKLIFT CAT 10 T', 'forklift'],
            ['SKID STEER LOADER (SSL CATERPILLAR 226B3)', 'loader'],
            ['SKID STEER LOADER A (SSL CATERPILLAR 226B3)', 'loader'],
            ['WHEEL LOADER A (LIU GONG S/N EXAMPLE123)', 'loader'],
            ['WHELL LOADER B (CATERPILLAR 980H)', 'loader'],
            ['TRACK DOZER C (CATERPILLAR D8R 01)', 'dozer'],
            ['TRACK DOZER F (CATERPILLAR D8R 04)', 'dozer'],
        ];
    }

    #[DataProvider('unresolvedDescriptions')]
    public function test_other_families_parts_and_ambiguous_names_keep_the_empty_state(mixed $description): void
    {
        $this->assertNull(app(AssetIllustration::class)->forAsset([
            'description' => $description,
            'hierarchy_category' => 'equipment',
        ]));
    }

    public static function unresolvedDescriptions(): array
    {
        return array_map(fn ($description) => [$description], [
            'GENERATOR TRANSFORMER 730 MVA',
            'FAN',
            'MOTOR RAW WATER PUMP A',
            'RAW WATER PUMP A & B',
            'RAW WATER PUMP A VALVE',
            'DOSING PUMP A',
            'MOTOR BELT CONVEYOR 3',
            'BELT CONVEYOR 3 DRIVE',
            'SCREW CONVEYOR 3',
            'BELT CONVEYOR 3 & 4',
            'CONTROL VALVE RAW WATER TANK',
            '[C] RAW WATER PUMP A',
            'GENERATOR & RECTIFIER TRANSFORMER A OF CHLORINE PLANT',
            'CURRENT TRANSFORMER A',
            'BOILER TRANSFORMER A MOTOR',
            'TRANSFORMER OIL PUMP A',
            'BOILER TRANSFORMER A & B',
            'MOTOR PRIMARY AIR FAN A',
            'PRIMARY AIR FAN A MOTOR',
            'PRIMARY AIR FAN A DAMPER',
            'PRIMARY AIR FAN A & B',
            'OIL FREE SCREW TYPE AIR COMPRESSOR A MOTOR',
            'PISTON AIR COMPRESSOR A',
            'PULVERIZER (MILL) A GEARBOX',
            'ELECTRIC HOIST MOTOR TURBINE AREA',
            'ELECTRIC HOIST BOILER AREA INSPECTION',
            'MANUAL CHAIN HOIST BOILER AREA',
            'COAL FEEDER A MOTOR',
            'COAL FEEDER A & B',
            'COAL FEEDER H',
            'MOTOR COAL FEEDER A',
            'BELT FEEDER 52',
            'BELT FEEDER (BF) 59',
            'BELT FEEDER A (JH 8 D)',
            'BELT FEEDER (BF) 52 DRIVE',
            'VIBRATING FEEDER 85',
            'VIBRATING FEEDER 81 MOTOR',
            'COAL CRUSHER A',
            'COAL CRUSHER C MOTOR',
            'CCCW HEAT EXCHANGER A VALVE',
            'CCCW HEAT EXCHANGER C',
            'OIL HEAT EXCHANGER A',
            'AIR PREHEATER C',
            'AIR PREHEATER A DRIVE',
            'AIR PREHEATER A SOOT BLOWER',
            'DESICANT AIR DRYER D',
            'DESICANT AIR DRYER A VALVE',
            'H2 DRYER A',
            'INSTRUMENT AIR RECEIVER TANK PRESSURE GAUGE',
            'PRESSURE TANK A',
            'TRAVELLING SCREEN D',
            'TRAVELLING SCREEN A MOTOR',
            'TRAVELLING SCREEN A & B',
            'VACUUM PUMP D',
            'FUEL OIL PUMP D',
            'LIGHT OIL TRANSFER PUMP C',
            'TURBINE BEARING OIL PUMP MOTOR',
            'CIRCULATING WATER PUMP D',
            'CONDENSATE EXTRACTION PUMP C',
            'BOILER CIRCULATING PUMP (6KV) BCP D',
            'BOILER CIRCULATING PUMP (10KV) BCP A',
            'BOOSTER PUMP OF TURBINE DRIVEN FEED PUMP C',
            'SEA WATER INTAKE PUMP A (DESAL SUPPLY PUMP B)',
            'SEA WATER INTAKE PUMP C (DESAL SUPPLY PUMP C)',
            'SEAWATER BOOSTER PUMP A OF UNKNOWN PLANT',
            'BACKWASHING PUMP A OF UNKNOWN SYSTEM',
            'DISTILLATE PUMP C',
            'SHUTDOWN COOLING WATER PUMP A',
            'DIVERTER GATE 2',
            'DIVERTER GATE (DG) 55/D',
            'DIVERTER GATE 54 (INLET HOPPER JH 8A)',
            'DIVERTER GATE BC 03 STRE',
            'DIVERTER GATE 1 ACTUATOR',
            'FLASH TANK A (13 M3)',
            'FLASH TANK B (26 M3)',
            'FLASH TANK C (26 M3)',
            'BLOW-OFF FLASH VESSEL TANK VALVE',
            'ROOTS BLOWER C OF CPP REGENERATION',
            'ROOTS BLOWER A OF UNKNOWN SYSTEM',
            'ASH CONTAINING WATER AERATION BLOWER A FILTER',
            'HP HEATER 4',
            'LP HEATER 4',
            'LP HEATER 7C',
            'HP HEATER 1 & 2',
            'HP HEATER 1 DRAIN VALVE',
            'ELECTRIC ROOM HEATER 1',
            'ASH CONTAINING WATER SLUDGE PUMP C',
            'DEHYDRATOR SLUDGE SUPPLY PUMP C',
            'MIXED REGENERATIVE WASTEWATER PUMP C',
            'WASTE WATER PUMP C USED FOR CPP REGENERATION',
            'WASTE WATER PUMP A USED FOR UNKNOWN SYSTEM',
            'WASTE WATER PUMP FOR UNKNOWN POND',
            'VALVE WASTE WATER PUMP FOR STORAGE POND WWTP',
            'WASTE WATER PUMP FOR STORAGE POND WWTP MOTOR',
            'WASTE WATER PUMP A USED FOR CPP REGENERATION SEAL',
            'CONTINUOUS DOSING PUMP C',
            'ACID DOSING EQUIPMENT SET (INCLUDE TANK & PUMP)',
            'ALKALI DOSING EQUIPMENT SET (INCLUDE TANK & PUMP)',
            'SEAWATER MOTOR DRIVEN FIRE FIGHTING PUMP',
            'FRESH WATER DIESEL DRIVEN FIRE FIGHTING PUMP ENGINE',
            'FRESH WATER MOTOR DRIVEN FIRE FIGHTING PUMP MOTOR',
            'JOCKEY PUMP C',
            'JOCKEY PUMP A & B',
            'EH OIL FOR BFPT',
            'EH OIL FOR TURBINE',
            'LINE TRANSFER ROW 1 ESP',
            'STRUCTURE & MOTOR TRAVELLING FOR STRE',
            'TILTING SOFA',
            'FINAL NEUTRALIZATION OF WWTP',
            'BAHAN BAKAR JUMPUTAN PADAT (BPJB)',
            'PURIFIED WATER OF WWTP',
            'WORKSHOP EQUIPMENTS',
            'STRE CABLE CHAIN SYSTEM 11 KV',
            'STRUCTURE OF UNKNOWN FOUNDATION',
            'MAGNETIC SEPARATOR 81 (81A & 82B)',
            'OIL GUN LAYER XX',
            'ACID METERING SET FOR UNKNOWN PLANT',
            'DUST SUPRESSION SYSTEM JUNCTION HOUSE 8E',
            'FIRE ALARM SYSTEM AREA UNKNOWN',
            '220V BATTERY BANK FOR UNKNOWN UPS (580AH)',
            'GENERATOR & RECTIFIER TRANSFORMER B OF CHLORINE PLANT',
            'WIND TURBINE GEARBOX',
            'SOLAR PANEL INVERTER',
            'AIR HANDLING UNIT UNKNOWN AREA',
            'AIR HANDLING UNIT CCB AREA FAN',
            'PLC FOR UNKNOWN SYSTEM',
            'CATHODIC PROTECTION RECTIFIER FOR UNKNOWN PUMP',
            'ESP A TRANSFORMER-RECTIFIER FIELD 5',
            'METAL DETECTOR C',
            'MIXED BED D',
            'HIGH FLOW RATE MIXED BED D OF CPP SYSTEM',
            'SECONDARY AIR DAMPER LAYER Z',
            'BOILER FEED PUMP TURBINE (BFPT) C',
            'SHORT RETRACTABLE SOOTBLOWER F',
            'LONG RETRACTABLE SOOTBLOWER UNKNOWN SIDE',
            'DEBRIS FILTER CW PIPE TO CONDENSER C',
            'DUMP TRUCK (HINO) 05',
            'FIRE TRUCK A (UNKNOWN)',
            'FORKLIFT C',
            'WHEEL LOADER A (LIU GONG S/N BAD VALUE)',
            'TRACK DOZER C (CATERPILLAR D8R 04)',
            'CABINET FAN',
            'FAN FOR CONTROL CABINET',
            'FAN FOR DCS CABINET FOR ESP SYSTEM',
            'DCS CABINET FOR UNKNOWN SYSTEM',
            'HVAC PLC PANEL FOR CENTRAL CONTROL BUILDING FAN',
            'DOOR DCS CABINET FOR ESP SYSTEM',
            'DCS SERVER CABINET SYSTEM 4',
            'ESP A HIGH VOLTAGE (HV) CONTROL CABINET FIELD 5',
            'SCREEN WASH PUMP A (MOTOR)',
            'SCREEN WASH PUMP A (UNVERIFIED MODEL)',
            'SCREEN WASH PUMP B (KSB)',
            'DOOR OF CONTROL PANEL',
            'SPARE CONTROL CABINET',
            'CABINET TERMINAL',
            'FUSE CONTROL PANEL',
            'WALL PANEL',
            'PANEL',
            'CONTINUOUS EMISSION MONITORING SYSTEM',
            '',
            null,
            ['CABINET'],
            str_repeat('A', 1001).' CABINET',
        ]);
    }

    #[DataProvider('nonEquipmentCategories')]
    public function test_hierarchy_categories_and_missing_metadata_are_not_guessed(?string $category): void
    {
        foreach (self::renderedFamilies() as [$description]) {
            $this->assertNull(app(AssetIllustration::class)->forAsset([
                'description' => $description,
                'hierarchy_category' => $category,
            ]));
        }
    }

    public static function nonEquipmentCategories(): array
    {
        return array_map(fn ($category) => [$category], ['system', 'component', 'part', 'unknown', null]);
    }

    #[DataProvider('renderedFamilies')]
    public function test_asset_detail_labels_the_illustration_without_new_requests_or_source_writes(string $description, string $family, string $label, string $category = 'equipment'): void
    {
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        $asset = [
            'canonical_id' => 'asset:BSR:CABINET-TEST',
            'source_asset_number' => 'CABINET-TEST',
            'site_code' => 'BSR',
            'organization_code' => 'IP',
            'description' => $description,
            'registered' => false,
            'hierarchy_category' => $category,
            'scope_basis' => 'SOURCE_PARENT_CHAIN',
        ];
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($asset)]);
        $user = User::factory()->create(['roles' => ['ENGINEER']])->refresh();
        $response = $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])
            ->get(route('assets.show', $asset['canonical_id']));
        $response->assertOk()
            ->assertSee('src="/images/asset-families/'.$family.'-illustration-v1.png"', false)
            ->assertSee('Ilustrasi generik · '.$label)
            ->assertSee('Bukan foto aset aktual. Belum diverifikasi engineer.')
            ->assertSee('Bentuk dan susunan bukan spesifikasi alat.')
            ->assertSee('Menunggu cross-check engineer.')
            ->assertSee('Read only')
            ->assertDontSee('Belum ada gambar')
            ->assertDontSee('<canvas', false)
            ->assertDontSee('type="file"', false);
        Http::assertSentCount(1);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public static function renderedFamilies(): array
    {
        return [
            ['AIR HANDLING UNIT CCB AREA', 'hvac-unit', 'Unit HVAC'],
            ['ACID METERING SET FOR MIXED BED', 'chemical-dosing-kit', 'Paket proses / fluida'],
            ['DELUGE & SPRINKLER SYSTEM AREA TURBINE & TRAFO', 'fire-protection-kit', 'Paket proteksi kebakaran'],
            ['DUST SUPRESSION SYSTEM JUNCTION HOUSE 8D', 'dust-spray-kit', 'Sistem spray / debu'],
            ['MOTOR TURBINE BEARING OIL PUMP', 'electric-machine', 'Mesin listrik'],
            ['110V BATTERY BANK A (600AH)', 'battery-bank', 'Bank baterai'],
            ['TURBINE TURNING GEAR', 'gear-assembly', 'Mekanisme gear'],
            ['AC NON-SEGREGATED PHASE BUSDUCT (NPB) TO EXCT', 'busduct', 'Busduct / busbar'],
            ['150KV LIGHTNING ARRESTER (LA)', 'lightning-arrester', 'Lightning arrester'],
            ['COMPRESSOR BUILDING & ESP PROPER BUILDING', 'industrial-building', 'Bangunan'],
            ['HANGER STRUCTURES OF BOILER HOUSE', 'structural-support', 'Struktur penyangga'],
            ['COAL YARD 2', 'industrial-site', 'Area / infrastruktur'],
            ['SETTLING BASIN PULVERIZER (MILL)', 'water-basin', 'Bak / kolam penampung'],
            ['CHIMNEY (STACK)', 'industrial-chimney', 'Cerobong'],
            ['OUTDOOR LIGHTING COAL HANDLING AREA', 'outdoor-lighting', 'Penerangan luar'],
            ['MICRO OIL BURNER', 'industrial-burner', 'Burner / ignitor'],
            ['COAL SAMPLER UNIT JH8D', 'coal-sampler', 'Sampler material'],
            ['DRY ASH UNLOADER', 'dry-ash-unloader', 'Unloader material'],
            ['ELECTROSTATIC PRECIPITATOR B CHAMBER COLLECTING/EMITING RAPPER', 'rapper-mechanism', 'Mekanisme rapper'],
            ['MAGNETIC SEPARATOR 81 (81A & 81B)', 'magnetic-separator', 'Magnetic separator'],
            ['STRE CABLE CHAIN SYSTEM 10.5 KV', 'cable-chain', 'Cable carrier'],
            ['ELEVATOR', 'industrial-elevator', 'Elevator'],
            ['RESIN HANDLING BARROW', 'utility-barrow', 'Troli / barrow'],
            ['SOLAR PANEL', 'solar-panel', 'Panel surya'],
            ['TELEPHONE CCR', 'desk-telephone', 'Telepon'],
            ['WIND TURBINE', 'wind-turbine', 'Turbin angin'],
            ['FAN VIBRATION MONITORING CABINET', 'control-cabinet', 'Kabinet / panel / kontrol'],
            ['RAW WATER PUMP A', 'water-pump', 'Pompa'],
            ['BELT CONVEYOR (BC) 48', 'belt-conveyor', 'Conveyor'],
            ['FUEL OIL TANK', 'storage-tank', 'Wadah penyimpanan'],
            ['GENERATOR TRANSFORMER (GT) 730 MVA 525/20 KV', 'power-transformer', 'Transformer / rectifier'],
            ['PRIMARY AIR FAN A', 'industrial-fan', 'Fan industri'],
            ['OIL FREE SCREW TYPE AIR COMPRESSOR A', 'screw-air-compressor', 'Kompresor udara screw'],
            ['PULVERIZER (MILL) A', 'coal-pulverizer', 'Pulverizer / coal mill'],
            ['ELECTRIC HOIST BOILER AREA', 'electric-hoist', 'Electric hoist'],
            ['COAL FEEDER A', 'coal-feeder', 'Coal feeder'],
            ['BELT FEEDER (BF) 52', 'belt-feeder', 'Belt feeder'],
            ['VIBRATING FEEDER 81', 'vibrating-feeder', 'Vibrating feeder'],
            ['COAL CRUSHER C', 'coal-crusher', 'Crusher'],
            ['CCCW HEAT EXCHANGER A', 'heat-exchanger', 'Heat exchanger'],
            ['AIR PREHEATER A', 'air-preheater', 'Air preheater'],
            ['DESICANT AIR DRYER A', 'desiccant-air-dryer', 'Dryer'],
            ['INSTRUMENT AIR RECEIVER TANK', 'air-receiver', 'Vessel / tangki'],
            ['TRAVELLING SCREEN A', 'travelling-screen', 'Screen / rack'],
            ['VACUUM PUMP A', 'vacuum-pump', 'Pompa vakum'],
            ['FUEL OIL PUMP A', 'oil-pump', 'Pompa oli / bahan bakar'],
            ['CIRCULATING WATER PUMP A', 'circulating-water-pump', 'Circulating water pump'],
            ['CONDENSATE EXTRACTION PUMP A', 'condensate-extraction-pump', 'Condensate extraction pump'],
            ['BOILER CIRCULATING PUMP (6KV) BCP A', 'boiler-circulating-pump', 'Boiler circulating pump'],
            ['BOOSTER PUMP OF TURBINE DRIVEN FEED PUMP A', 'feedwater-booster-pump', 'Feedwater booster pump'],
            ['DIVERTER GATE 1', 'diverter-gate', 'Diverter gate'],
            ['AUXILIARY STEAM DRAIN FLASH TANK', 'flash-vessel', 'Flash / blowdown vessel'],
            ['ASH CONTAINING WATER AERATION BLOWER A', 'industrial-blower', 'Blower industri'],
            ['HP HEATER 1', 'feedwater-heater', 'Feedwater heater'],
            ['ASH CONTAINING WATER SLUDGE PUMP A', 'sludge-pump', 'Pompa slurry / sludge'],
            ['WASTE WATER PUMP A USED FOR CPP REGENERATION', 'wastewater-pump', 'Pompa limbah / drainase'],
            ['CONTINUOUS DOSING PUMP A', 'dosing-pump', 'Dosing pump'],
            ['FRESH WATER DIESEL DRIVEN FIRE FIGHTING PUMP', 'diesel-fire-pump', 'Diesel fire pump'],
            ['FRESH WATER MOTOR DRIVEN FIRE FIGHTING PUMP', 'electric-fire-pump', 'Electric fire pump'],
            ['JOCKEY PUMP A', 'jockey-pump', 'Jockey pump'],
            ['RAW WATER PUMP A INSTRUMENTATION DEVICES', 'instrumentation-kit', 'Instrumentasi / monitoring'],
            ['COAL PIPE A', 'part-piping', 'Perpipaan'],
            ['TURBINE VALVE', 'part-valve-damper', 'Valve / damper / gate'],
            ['AIR HEATER SOOTBLOWER', 'sootblower', 'Sootblower'],
            ['BOILER FEED PUMP TURBINE (BFPT) A', 'steam-turbine', 'Turbin uap'],
            ['DEBRIS FILTER CW PIPE TO CONDENSER A', 'process-filter', 'Filter / pengolahan'],
            ['VACUUM TRUCK', 'truck', 'Truk'],
            ['EXCAVATOR A (CATERPILLAR 320)', 'excavator', 'Excavator'],
            ['FORKLIFT A', 'forklift', 'Forklift'],
            ['WHELL LOADER B (CATERPILLAR 980H)', 'loader', 'Loader'],
            ['TRACK DOZER C (CATERPILLAR D8R 01)', 'dozer', 'Dozer'],
        ];
    }

    public function test_every_rendered_family_has_intact_local_media_and_provenance(): void
    {
        $manifest = json_decode(file_get_contents(resource_path('data/asset-illustrations-provenance.json')), true, 32, JSON_THROW_ON_ERROR);
        $this->assertSame('GENERIC_AI_ILLUSTRATION', $manifest['kind']);
        $this->assertSame('NOT_ENGINEER_VERIFIED', $manifest['review_status']);
        $families = array_column($manifest['assets'], null, 'family');
        $this->assertCount(count($manifest['assets']), $families);
        $expectedFamilies = array_unique(array_column([...self::renderedFamilies(), ...self::partFamilies()], 1));
        $this->assertCount(count($expectedFamilies), $families);

        foreach ([...self::renderedFamilies(), ...self::partFamilies()] as [, $family]) {
            $this->assertArrayHasKey($family, $families);
            $entry = $families[$family];
            $path = 'public/images/asset-families/'.$family.'-illustration-v1.png';
            $this->assertSame($path, $entry['file']);
            $this->assertSame($entry['bytes'], filesize(base_path($path)));
            $this->assertSame($entry['sha256'], hash_file('sha256', base_path($path)));
            $dimensions = getimagesize(base_path($path));
            $this->assertSame($entry['width'], $dimensions[0]);
            $this->assertSame($entry['height'], $dimensions[1]);
            $this->assertSame('image/png', $dimensions['mime']);
            $this->assertNotEmpty($entry['prompt'] ?? $entry['prompt_summary'] ?? null);
        }
    }

    public function test_missing_local_media_fails_closed_without_an_external_fallback(): void
    {
        $original = public_path();
        try {
            app()->usePublicPath(base_path('tests/Fixtures/no-asset-media'));
            foreach (self::renderedFamilies() as [$description]) {
                $this->assertNull(app(AssetIllustration::class)->forAsset([
                    'description' => $description,
                    'hierarchy_category' => 'equipment',
                ]));
            }
            foreach (self::partFamilies() as [$description]) {
                $this->assertNull(app(AssetIllustration::class)->forAsset([
                    'description' => $description,
                    'hierarchy_category' => 'part',
                ]));
            }
        } finally {
            app()->usePublicPath($original);
        }
    }
}

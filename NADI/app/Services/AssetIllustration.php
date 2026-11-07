<?php

namespace App\Services;

class AssetIllustration
{
    private const FAMILIES = [
        'hvac-unit' => ['label' => 'Unit HVAC', 'file' => 'hvac-unit-illustration-v1.png'],
        'chemical-dosing-kit' => ['label' => 'Paket proses / fluida', 'file' => 'chemical-dosing-kit-illustration-v1.png'],
        'fire-protection-kit' => ['label' => 'Paket proteksi kebakaran', 'file' => 'fire-protection-kit-illustration-v1.png'],
        'dust-spray-kit' => ['label' => 'Sistem spray / debu', 'file' => 'dust-spray-kit-illustration-v1.png'],
        'electric-machine' => ['label' => 'Mesin listrik', 'file' => 'electric-machine-illustration-v1.png'],
        'battery-bank' => ['label' => 'Bank baterai', 'file' => 'battery-bank-illustration-v1.png'],
        'gear-assembly' => ['label' => 'Mekanisme gear', 'file' => 'gear-assembly-illustration-v1.png'],
        'busduct' => ['label' => 'Busduct / busbar', 'file' => 'busduct-illustration-v1.png'],
        'lightning-arrester' => ['label' => 'Lightning arrester', 'file' => 'lightning-arrester-illustration-v1.png'],
        'industrial-building' => ['label' => 'Bangunan', 'file' => 'industrial-building-illustration-v1.png'],
        'structural-support' => ['label' => 'Struktur penyangga', 'file' => 'structural-support-illustration-v1.png'],
        'industrial-site' => ['label' => 'Area / infrastruktur', 'file' => 'industrial-site-illustration-v1.png'],
        'water-basin' => ['label' => 'Bak / kolam penampung', 'file' => 'water-basin-illustration-v1.png'],
        'industrial-chimney' => ['label' => 'Cerobong', 'file' => 'industrial-chimney-illustration-v1.png'],
        'outdoor-lighting' => ['label' => 'Penerangan luar', 'file' => 'outdoor-lighting-illustration-v1.png'],
        'industrial-burner' => ['label' => 'Burner / ignitor', 'file' => 'industrial-burner-illustration-v1.png'],
        'coal-sampler' => ['label' => 'Sampler material', 'file' => 'coal-sampler-illustration-v1.png'],
        'dry-ash-unloader' => ['label' => 'Unloader material', 'file' => 'dry-ash-unloader-illustration-v1.png'],
        'rapper-mechanism' => ['label' => 'Mekanisme rapper', 'file' => 'rapper-mechanism-illustration-v1.png'],
        'magnetic-separator' => ['label' => 'Magnetic separator', 'file' => 'magnetic-separator-illustration-v1.png'],
        'cable-chain' => ['label' => 'Cable carrier', 'file' => 'cable-chain-illustration-v1.png'],
        'industrial-elevator' => ['label' => 'Elevator', 'file' => 'industrial-elevator-illustration-v1.png'],
        'utility-barrow' => ['label' => 'Troli / barrow', 'file' => 'utility-barrow-illustration-v1.png'],
        'solar-panel' => ['label' => 'Panel surya', 'file' => 'solar-panel-illustration-v1.png'],
        'desk-telephone' => ['label' => 'Telepon', 'file' => 'desk-telephone-illustration-v1.png'],
        'wind-turbine' => ['label' => 'Turbin angin', 'file' => 'wind-turbine-illustration-v1.png'],
        'control-cabinet' => ['label' => 'Kabinet / panel / kontrol', 'file' => 'control-cabinet-illustration-v1.png'],
        'water-pump' => ['label' => 'Pompa', 'file' => 'water-pump-illustration-v1.png'],
        'belt-conveyor' => ['label' => 'Conveyor', 'file' => 'belt-conveyor-illustration-v1.png'],
        'storage-tank' => ['label' => 'Wadah penyimpanan', 'file' => 'storage-tank-illustration-v1.png'],
        'power-transformer' => ['label' => 'Transformer / rectifier', 'file' => 'power-transformer-illustration-v1.png'],
        'industrial-fan' => ['label' => 'Fan industri', 'file' => 'industrial-fan-illustration-v1.png'],
        'screw-air-compressor' => ['label' => 'Kompresor udara screw', 'file' => 'screw-air-compressor-illustration-v1.png'],
        'coal-pulverizer' => ['label' => 'Pulverizer / coal mill', 'file' => 'coal-pulverizer-illustration-v1.png'],
        'electric-hoist' => ['label' => 'Electric hoist', 'file' => 'electric-hoist-illustration-v1.png'],
        'coal-feeder' => ['label' => 'Coal feeder', 'file' => 'coal-feeder-illustration-v1.png'],
        'belt-feeder' => ['label' => 'Belt feeder', 'file' => 'belt-feeder-illustration-v1.png'],
        'vibrating-feeder' => ['label' => 'Vibrating feeder', 'file' => 'vibrating-feeder-illustration-v1.png'],
        'coal-crusher' => ['label' => 'Crusher', 'file' => 'coal-crusher-illustration-v1.png'],
        'heat-exchanger' => ['label' => 'Heat exchanger', 'file' => 'heat-exchanger-illustration-v1.png'],
        'air-preheater' => ['label' => 'Air preheater', 'file' => 'air-preheater-illustration-v1.png'],
        'desiccant-air-dryer' => ['label' => 'Dryer', 'file' => 'desiccant-air-dryer-illustration-v1.png'],
        'air-receiver' => ['label' => 'Vessel / tangki', 'file' => 'air-receiver-illustration-v1.png'],
        'travelling-screen' => ['label' => 'Screen / rack', 'file' => 'travelling-screen-illustration-v1.png'],
        'vacuum-pump' => ['label' => 'Pompa vakum', 'file' => 'vacuum-pump-illustration-v1.png'],
        'oil-pump' => ['label' => 'Pompa oli / bahan bakar', 'file' => 'oil-pump-illustration-v1.png'],
        'circulating-water-pump' => ['label' => 'Circulating water pump', 'file' => 'circulating-water-pump-illustration-v1.png'],
        'condensate-extraction-pump' => ['label' => 'Condensate extraction pump', 'file' => 'condensate-extraction-pump-illustration-v1.png'],
        'boiler-circulating-pump' => ['label' => 'Boiler circulating pump', 'file' => 'boiler-circulating-pump-illustration-v1.png'],
        'feedwater-booster-pump' => ['label' => 'Feedwater booster pump', 'file' => 'feedwater-booster-pump-illustration-v1.png'],
        'diverter-gate' => ['label' => 'Diverter gate', 'file' => 'diverter-gate-illustration-v1.png'],
        'flash-vessel' => ['label' => 'Flash / blowdown vessel', 'file' => 'flash-vessel-illustration-v1.png'],
        'industrial-blower' => ['label' => 'Blower industri', 'file' => 'industrial-blower-illustration-v1.png'],
        'feedwater-heater' => ['label' => 'Feedwater heater', 'file' => 'feedwater-heater-illustration-v1.png'],
        'sludge-pump' => ['label' => 'Pompa slurry / sludge', 'file' => 'sludge-pump-illustration-v1.png'],
        'wastewater-pump' => ['label' => 'Pompa limbah / drainase', 'file' => 'wastewater-pump-illustration-v1.png'],
        'dosing-pump' => ['label' => 'Dosing pump', 'file' => 'dosing-pump-illustration-v1.png'],
        'diesel-fire-pump' => ['label' => 'Diesel fire pump', 'file' => 'diesel-fire-pump-illustration-v1.png'],
        'electric-fire-pump' => ['label' => 'Electric fire pump', 'file' => 'electric-fire-pump-illustration-v1.png'],
        'jockey-pump' => ['label' => 'Jockey pump', 'file' => 'jockey-pump-illustration-v1.png'],
        'instrumentation-kit' => ['label' => 'Instrumentasi / monitoring', 'file' => 'instrumentation-kit-illustration-v1.png'],
        'sootblower' => ['label' => 'Sootblower', 'file' => 'sootblower-illustration-v1.png'],
        'steam-turbine' => ['label' => 'Turbin uap', 'file' => 'steam-turbine-illustration-v1.png'],
        'process-filter' => ['label' => 'Filter / pengolahan', 'file' => 'process-filter-illustration-v1.png'],
        'truck' => ['label' => 'Truk', 'file' => 'truck-illustration-v1.png'],
        'excavator' => ['label' => 'Excavator', 'file' => 'excavator-illustration-v1.png'],
        'forklift' => ['label' => 'Forklift', 'file' => 'forklift-illustration-v1.png'],
        'loader' => ['label' => 'Loader', 'file' => 'loader-illustration-v1.png'],
        'dozer' => ['label' => 'Dozer', 'file' => 'dozer-illustration-v1.png'],
        'part-temperature-sensor' => ['label' => 'Sensor suhu', 'file' => 'part-temperature-sensor-illustration-v1.png'],
        'part-dial-gauge' => ['label' => 'Gauge / thermometer', 'file' => 'part-dial-gauge-illustration-v1.png'],
        'part-industrial-switch' => ['label' => 'Process switch', 'file' => 'part-industrial-switch-illustration-v1.png'],
        'part-transmitter' => ['label' => 'Transmitter', 'file' => 'part-transmitter-illustration-v1.png'],
        'part-valve-damper' => ['label' => 'Valve / damper / gate', 'file' => 'part-valve-damper-illustration-v1.png'],
        'part-piping' => ['label' => 'Perpipaan', 'file' => 'part-piping-illustration-v1.png'],
    ];

    /** Presentation-only family inference, never an asset identity or source classification. */
    public function forAsset(array $asset): ?array
    {
        $category = $asset['hierarchy_category'] ?? null;
        if (! in_array($category, ['equipment', 'part'], true)
            || ! is_string($asset['description'] ?? null)
            || strlen($asset['description']) > 1000) {
            return null;
        }

        $description = trim(preg_replace('/\s+/u', ' ', strtoupper($asset['description'])) ?? '');
        if ($description === '') {
            return null;
        }

        if ($category === 'part') {
            // Part context may mention a pump, motor or bearing. Match the part
            // itself; never send it through whole-equipment family inference.
            $family = $this->partFamily($description);
        } else {
            $additionalFamily = $this->additionalEquipmentFamily($description);
            $explicitSubject = $additionalFamily !== null || $this->isExplicitCabinet($description)
                || $this->isExplicitWastewaterPump($description)
                || $this->isExplicitGenericPump($description);
            if (($additionalFamily === null && preg_match('/\b(?:SPARE|PARTS?|COMPONENT|DOOR|HINGE|HANDLE|CABLE|TERMINAL|FUSE|REPAIR|FOUNDATION)\b/', $description))
                || (! $explicitSubject && preg_match('/\bFOR\b|\bOF\s+(?:THE\s+)?(?:PANEL|CABINET|MCC)\b/', $description))) {
                return null;
            }
            $family = $additionalFamily ?? $this->family($description);
        }

        if ($family === null) {
            return null;
        }

        $media = self::FAMILIES[$family];
        $path = 'images/asset-families/'.$media['file'];
        if (! is_file(public_path($path))) {
            return null;
        }

        return [
            'family' => $family,
            'label' => $media['label'].($category === 'part' ? ' (Part)' : ''),
            'path' => '/'.$path,
            'kind' => 'GENERIC_AI_ILLUSTRATION',
            'review_status' => 'NOT_ENGINEER_VERIFIED',
            'subject_level' => $category,
        ];
    }

    private function family(string $description): ?string
    {
        if ($this->isExplicitCabinet($description)) {
            return 'control-cabinet';
        }

        if ($this->isExplicitWastewaterPump($description)) {
            return 'wastewater-pump';
        }

        if ($this->isExplicitGenericPump($description)) {
            return 'water-pump';
        }

        // The terminal subject is a set of instruments, not the parent machine.
        if (preg_match('/^.+ INSTRUMENTATION DEVICES$/', $description)
            || preg_replace('/^\\[E\\]\\s*/', '', $description) === 'CONDENSATE POLISHING PLANT INSTRUMENTATION DEVICE') {
            return 'instrumentation-kit';
        }

        // The object noun must end the name. A pump/fan/transformer mentioned before
        // a cabinet or MCC is context, not the illustrated piece of equipment.
        if (preg_match('/\b(CABINET|PANEL|MCC)(?:\s+(?:[A-Z]|\d+|\([A-Z0-9 -]+\)))?$/', $description, $matches)
            && ($matches[1] !== 'PANEL'
                || preg_match('/\b(?:CONTROL|PROTECTION|DISTRIBUTION|INSTRUMENT|LOCAL|RELAY|RECORDING|MONITORING|PLC|DCS|POWER)\b/', $description))) {
            return 'control-cabinet';
        }

        // Ignore a literal display prefix only AFTER requiring the explicit Equipment
        // category. The prefix does not establish a category, source scope or identity.
        $name = preg_replace('/^\[E\]\s*/', '', $description);

        // Exact whole-name patterns avoid depicting a conveyor's instrument, motor,
        // structure or belt part as the whole conveyor assembly.
        if (preg_match('/^BELT CONVEYOR(?: \(BC\))? [0-9]{1,3}$/', $name)) {
            return 'belt-conveyor';
        }

        // Storage service only: pressure/air receivers, flash/blowdown vessels,
        // expansion tanks and fire-fighting systems remain unresolved.
        if (preg_match('/^(?:FOAM CONCENTRATE STORAGE|CONDENSATE STORAGE|DEMINERALIZED WATER|POTABLE WATER|RAW WATER|FUEL OIL) TANK(?: [A-Z])?$/', $name)) {
            return 'storage-tank';
        }

        // Limited water services. Do not generalize from PUMP to a vacuum/oil/dosing/
        // sludge pump, a pump motor, vertical circulating/extraction pump or system.
        if (preg_match('/^(?:RAW WATER|SCREEN WASH|POTABLE WATER BOOSTER|MAKE UP BOOSTER|CLOSED CYCLE COOLING WATER|CONDENSATE TRANSFER|ASH CONTAINING WATER BOOSTER) PUMP(?: [A-Z])?$/', $name)
            || preg_match('/^SCREEN WASH PUMP [AC] \(KSB\)$/', $name)
            || preg_match('/^(?:DEMINERALIZED WATER BOOSTER|DISTILLATE|DISTILLATE INJECTION|BRINE BLOW DOWN) PUMP [AB]$/', $name)
            || preg_match('/^SEAWATER BOOSTER PUMP [AB] OF CHLORINE PLANT$/', $name)
            || preg_match('/^SEA WATER INTAKE PUMP ([AB]) \(DESAL SUPPLY PUMP \1\)$/', $name)
            || preg_match('/^BACKWASHING PUMP [AB] OF CPP REGENERATION$/', $name)
            || preg_match('/^(?:SERVICE WATER TRANSFER PUMP TO JH 8A \(AREA COAL HANDLING\)|SHUTDOWN COOLING WATER PUMP)$/', $name)) {
            return 'water-pump';
        }

        // Power equipment only, never protection panels, dry transformers,
        // excitation units, ESP rectifier assemblies or current transformers.
        $rating = '[0-9]+(?:\.[0-9]+)?\s*MVA\s+[0-9]+(?:\.[0-9]+)?/[0-9]+(?:\.[0-9]+)?\s*KV';
        if (preg_match('~^(?:BOILER|MAINTENANCE|TURBINE|WATER SYSTEM|STATION SERVICE|LIGHTING|COAL HANDLING|ASH HANDLING) TRANSFORMER(?: [A-Z])?$~', $name)
            || preg_match('~^GENERATOR TRANSFORMER \(GT\) '.$rating.'$~', $name)
            || preg_match('~^STARTUP/STANDBY AUXILIARY TRANSFORMER \(S/SAT\) '.$rating.'$~', $name)
            || preg_match('~^UNIT AUXILIARY TRANSFORMER \(UAT\) [A-Z] '.$rating.'$~', $name)) {
            return 'power-transformer';
        }

        // Whole fan equipment names only. The illustration does not establish
        // actual fan topology, dimensions, impeller arrangement or drive design.
        if (preg_match('/^(?:PRIMARY AIR|INDUCED DRAFT|FORCED DRAFT|SEALING AIR|FLAME MONITORS COOLING AIR) FAN [A-Z]$/', $name)
            || preg_match('/^(?:INDUCED|FORCED) DRAFT FAN OF START UP BOILER$/', $name)) {
            return 'industrial-fan';
        }

        if (preg_match('/^OIL FREE SCREW TYPE AIR COMPRESSOR [A-Z]$/', $name)) {
            return 'screw-air-compressor';
        }

        if (preg_match('/^PULVERIZER \(MILL\) [A-G]$/', $name)) {
            return 'coal-pulverizer';
        }

        if (preg_match('/^ELECTRIC HOIST (?:TURBINE|BOILER|COAL-ASH|AUXILIARY PLANT) AREA$/', $name)) {
            return 'electric-hoist';
        }

        // Keep each material-handling subject separate. These observed whole
        // names do not include shared instrumentation, motors or feeder parts.
        if (preg_match('/^COAL FEEDER [A-G]$/', $name)) {
            return 'coal-feeder';
        }

        if (preg_match('/^BELT FEEDER (?:\(BF\) (?:52|53)|59|[CD] \(JH 8 D\))$/', $name)) {
            return 'belt-feeder';
        }

        if (preg_match('/^VIBRATING FEEDER (?:81|82|83|84)$/', $name)) {
            return 'vibrating-feeder';
        }

        if (preg_match('/^COAL CRUSHER [CD]$/', $name)) {
            return 'coal-crusher';
        }

        // Construction is illustrative, not evidence of actual exchanger type.
        if (preg_match('/^CCCW HEAT EXCHANGER [AB]$/', $name)) {
            return 'heat-exchanger';
        }

        if (preg_match('/^AIR PREHEATER [AB]$/', $name)) {
            return 'air-preheater';
        }

        // Preserve the source's DESICANT spelling in this narrow match.
        if (preg_match('/^DESICANT AIR DRYER [ABC]$/', $name)) {
            return 'desiccant-air-dryer';
        }

        if (preg_match('/^(?:INSTRUMENT|SERVICE) AIR RECEIVER TANK$/', $name)) {
            return 'air-receiver';
        }

        if (preg_match('/^TRAVELLING SCREEN [ABC]$/', $name)) {
            return 'travelling-screen';
        }

        // Service-specific illustrations, not a universal PUMP fallback.
        // Stage count, actual orientation and drive topology remain unverified.
        if (preg_match('/^(?:VACUUM PUMP [ABC]|CONDENSER WATERBOX VACUUM PRIMING PUMP)$/', $name)) {
            return 'vacuum-pump';
        }

        if (preg_match('/^(?:FUEL OIL PUMP [ABC]|LIGHT OIL TRANSFER PUMP [AB]|DC TURBINE EMERGENCY OIL PUMP|SEAL OIL BACK UP PUMP|TURBINE BEARING OIL PUMP)$/', $name)) {
            return 'oil-pump';
        }

        if (preg_match('/^CIRCULATING WATER PUMP [ABC]$/', $name)) {
            return 'circulating-water-pump';
        }

        if (preg_match('/^CONDENSATE EXTRACTION PUMP [AB]$/', $name)) {
            return 'condensate-extraction-pump';
        }

        if (preg_match('/^BOILER CIRCULATING PUMP \(6KV\) BCP [ABC]$/', $name)) {
            return 'boiler-circulating-pump';
        }

        // A booster pump is the subject here. BOILER FEED PUMP TURBINE
        // is handled by the separate steam-turbine family, never this pump image.
        if (preg_match('/^BOOSTER PUMP OF TURBINE DRIVEN FEED PUMP [AB]$/', $name)) {
            return 'feedwater-booster-pump';
        }

        if (preg_match('/^DIVERTER GATE (?:\(DG\) (?:55\/C|56\/D)|(?:1|43|44|52|53|82|85|86|87|88|89|90)|54 \(INLET HOPPER JH 8D\)|BC 03 JH 8A|BC 04 STRE)$/', $name)) {
            return 'diverter-gate';
        }

        // Flash/blowdown service is not an atmospheric liquid storage tank.
        // Preserve observed spelling and exact paired capacity/name qualifiers.
        if (preg_match('/^(?:AUXILIARY STEAM DRAIN FLASH TANK|BLOW-OFF FLASH VESSEL TANK|CONTINOUS BLOWDOWN TANK|INTERMITTENT BLOWDOWN FLASH TANK|FLASH TANK A \(26 M3\)|FLASH TANK B \(13 M3\))$/', $name)) {
            return 'flash-vessel';
        }

        if (preg_match('/^(?:(?:ASH CONTAINING WATER|ESP HOPPER) AERATION BLOWER [AB]|ROOTS BLOWER [AB] OF CPP REGENERATION)$/', $name)) {
            return 'industrial-blower';
        }

        if (preg_match('/^(?:HP HEATER [1-3]|LP HEATER (?:5|6|7A|7B|8A|8B))$/', $name)) {
            return 'feedwater-heater';
        }

        if (preg_match('/^(?:ASH CONTAINING WATER (?:LIFT|SLUDGE|VACUUM CAN LIFT|VACUUM CAN SLUDGE)|DEHYDRATOR SLUDGE SUPPLY) PUMP [AB]$/', $name)) {
            return 'sludge-pump';
        }

        if (preg_match('/^(?:MIXED REGENERATIVE WASTEWATER PUMP [AB]|UNDERWATER PUMP OF WWTP SYSTEM \(LINGKUNGAN\)|UNIT DRAINAGE PIT DISCHARGE PUMP [AB])$/', $name)) {
            return 'wastewater-pump';
        }

        if (preg_match('/^(?:CONTINUOUS DOSING PUMP [AB]|IMPACT DOSING PUMP)$/', $name)) {
            return 'dosing-pump';
        }

        // Driver words qualify the pump subject, not a standalone motor/engine.
        if (preg_match('/^(?:FRESH WATER|SEAWATER) DIESEL DRIVEN FIRE FIGHTING PUMP$/', $name)) {
            return 'diesel-fire-pump';
        }

        if ($name === 'FRESH WATER MOTOR DRIVEN FIRE FIGHTING PUMP') {
            return 'electric-fire-pump';
        }

        if (preg_match('/^JOCKEY PUMP [AB]$/', $name)) {
            return 'jockey-pump';
        }

        return null;
    }

    private function additionalEquipmentFamily(string $description): ?string
    {
        $name = preg_replace('/^\[E\]\s*/', '', $description);

        // Generic family reuse follows the whole object subject, not its subtype.
        // Exact whole-name context clauses can bypass the generic token guards.
        // A cable carrier or structural foundation is itself the object, not a
        // machine part inferred from context. Prefix/suffix mutations cannot match.
        // Keep every pattern anchored and add prefix/suffix regression fixtures
        // with each extension; never place broad keyword inference here.
        $patterns = [
            'hvac-unit' => [
                '~^(?:AIR HANDLING UNIT (?:CCB|COMPRESSOR ROOM) AREA|AIR-COOLED LIQUID CHILLER)$~',
            ],
            'wind-turbine' => [
                '~^WIND TURBINE$~',
            ],
            'desk-telephone' => [
                '~^TELEPHONE CCR$~',
            ],
            'solar-panel' => [
                '~^SOLAR PANEL$~',
            ],
            'utility-barrow' => [
                '~^RESIN HANDLING BARROW$~',
            ],
            'industrial-elevator' => [
                '~^ELEVATOR$~',
            ],
            'travelling-screen' => [
                '~^TRASH RACK SYSTEM$~',
            ],
            'cable-chain' => [
                '~^STRE CABLE CHAIN SYSTEM 10\.5 KV$~',
            ],
            'magnetic-separator' => [
                '~^MAGNETIC SEPARATOR (?:81 \(81A & 81B\)|82 \(82A & 82B\)|FOR BC 4 STRE)$~',
            ],
            'rapper-mechanism' => [
                '~^ELECTROSTATIC PRECIPITATOR [AB] CHAMBER COLLECTING/EMITING RAPPER$~',
            ],
            'dry-ash-unloader' => [
                '~^DRY ASH UNLOADER$~',
            ],
            'coal-sampler' => [
                '~^COAL SAMPLER UNIT(?: JH8D)?$~',
            ],
            'industrial-burner' => [
                '~^(?:MICRO OIL BURNER|TILTING BURNER|STARTUP BOILER IGNITOR AND BURNER|OIL GUN LAYER (?:AB|CD|EF|FG))$~',
            ],
            'outdoor-lighting' => [
                '~^OUTDOOR LIGHTING (?:COAL HANDLING|UNIT) AREA$~',
            ],
            'industrial-chimney' => [
                '~^CHIMNEY \(STACK\)$~',
            ],
            'water-basin' => [
                '~^(?:MIXED REGENERATIVE WASTE WATER PIT|SETTLING BASIN(?: PULVERIZER \(MILL\))?|UNIT DRAINAGE PIT|WASTE WATER PIT OF CPP REGENERATION|WASTE WATER STORAGE POND)$~',
            ],
            'industrial-site' => [
                '~^(?:COAL YARD [12]|LANDSCAPING AREA COAL YARD|ROAD WAY|DINDING BUKIT)$~',
            ],
            'structural-support' => [
                '~^(?:HANGER STRUCTURES OF (?:BOILER|TURBINE) HOUSE|STRUCTURE OF TURBINE-GENERATOR FOUNDATION)$~',
            ],
            'industrial-building' => [
                '~^(?:ADMINISTRATION & SERVICE SAFETY CENTER BUILDING AREA|COMPRESSOR BUILDING & ESP PROPER BUILDING|FABA BUILDING|MAINTENANCE BUILDING AREA|WORKSHOP FACILITY BUILDING|STRUCTURE & BUILDING COAL HANDLING AREA|STRUCTURE & BUILDING LABORATORY & BOP BUILDING AREA|STRUCTURE & BUILDING OF WAREHOUSE FACILITY|STRUCTURES OF CENTRAL CONTROL BUILDING \(CCB\) & TURBINE HOUSE|STRUCTURES OF BOILER HOUSE & ESP AREA)$~',
            ],
            'lightning-arrester' => [
                '~^(?:150|500)KV LIGHTNING ARRESTER \(LA\)$~',
            ],
            'busduct' => [
                '~^(?:AC NON-SEGREGATED PHASE BUSDUCT \(NPB\) TO EXCT|DC NON-SEGREGATED PHASE BUSDUCT \(NPB\) FROM EXCT|ISOLATED PHASE BUS \(IPB\) 24KV 24000A|NON-SEGREGATED PHASE BUS \(NPB\) FROM (?:S/SAT|UAT [AB]))$~',
            ],
            'gear-assembly' => [
                '~^TURBINE TURNING GEAR$~',
            ],
            'battery-bank' => [
                '~^(?:110V BATTERY BANK [AB] \(600AH\)|110V BATTERY BANK COAL HANDLING \(100AH\)|220V BATTERY BANK \(2000AH\)|220V BATTERY BANK FOR MAIN UPS \(580AH\))$~',
            ],
            'electric-machine' => [
                '~^(?:MOTOR TURBINE BEARING OIL PUMP|GENERATOR QFSN-625-2 625MW 20KV 21227A|EMERGENCY DIESEL GENERATOR \(EDG\) 1020KW 400V 50HZ)$~',
            ],
            'dust-spray-kit' => [
                '~^(?:DUST SUPRESSION SYSTEM JUNCTION HOUSE 8[BCD]|SPRAY WATER SYSTEM FOR STRE)$~',
            ],
            'fire-protection-kit' => [
                '~^DELUGE & SPRINKLER SYSTEM AREA (?:BOILER|BOP|COAL HANDLING|TURBINE|TURBINE & TRAFO)$~',
                '~^HYDRANT/HOSEREEL AREA (?:ASH HANDLING & COAL HANDLING|BOILER|BOP|COAL HANDLING|TURBINE|TURBINE & TRAFO)$~',
                '~^(?:DRENCHER SPRINKLER/COOLING FIRE FIGHTING SYSTEM FUEL OIL TANK|LP CO2 SUPRESSION EQUIPMENT)$~',
                '~^FIRE ALARM SYSTEM AREA (?:BOILER|BOP|COAL HANDLING|TURBINE & TRAFO)$~',
            ],
            'chemical-dosing-kit' => [
                '~^(?:ACID|ALKALI) METERING SET FOR (?:MIXED BED|MIXED BED WTP|WWTP)$~',
                '~^(?:COAGULATION AID|DEHYDRANT|FLOCCULANT) METERING SET FOR WWTP$~',
                '~^(?:ACID|ALKALI) DOSING EQUIPMENT SET OF CPP \(INCLUDE TANK & PUMP\)$~',
                '~^(?:ANTIFOAM|ANTISCALANT|SODIUM BI SULPHITE|SODIUM HYDROXIDE) DOSING EQUIPMENT SET$~',
                '~^(?:LIME DOSING EQUIPMENT SET POTABLE WATER SYSTEM|SODIUM HYPOCHLORITE DOSING EQUIPMENT SET OF POTABLE WATER SYSTEM|SODIUM HYPOCHLORIT SET FOR WWTP)$~',
                '~^(?:ANTISCALANT|COAGULANT|FLOCCULANT) SET FOR ASH CONTAINING WATER$~',
                '~^(?:AMMONIA|HYDRAZINE|PHOSPHATE) SUPPLY AND DISTRIBUTION EQUIPMENT$~',
                '~^(?:ACID CLEANING EQUIPMENT SET|ACID CLEANING SET EQUIPMENTS OF CHLORINE PLANT|HYDROGEN \(H2\) PLANT \(FRAME I\)|MAKE UP PURE WATER AND ALKALINE SOLUTION SKID H2 PLANT|SODIUM HYPOCHLORITE GENERATOR SET)$~',
                '~^(?:CONDENSATE DESUPERHEATING SPRAY SYSTEM|CWP SEALING SYSTEM|EH OIL FOR (?:BFPT|TURBINE) PURIFICATION SYSTEM|GENERATOR SEAL OIL SYSTEM|GENERATOR STATOR COOLING WATER SYSTEM|HYDRAULIC SYSTEM FOR STRE|REPETITION COOLING DEVICE OF H2 PLANT|SERVICE WATER SYSTEM|TURBINE LUBE OIL(?: PURIFICATION)? SYSTEM)$~',
                '~^(?:ASH CONTAINING WATER PURIFYING SET [AB]|CLARIFIER OF WWTP|DEHYDRATOR INCLUDE SLUDGE HOPPER OF WWTP|FILTRASI & TANK HSD ALBES|MULTI EFFECT DESALINATION \(MED\) [AB]|OIL WATER SEPARATOR|SEWAGE TREATMENT EQUIPMENT SET)$~',
            ],
            'industrial-blower' => [
                '~^ROOTS FAN A, B, PIPING & AERATOR$~',
            ],
            'instrumentation-kit' => [
                '~^(?:AUTOMATIC GENERATION CONTROL \(AGC\) SYSTEM|AVR UNITROL 5000 STATIC EXCITATION SYSTEM|BALANCE OF PLANT \(BOP\) AUXILIARY NETWORK SYSTEM CONTROL|CCTV SYSTEM|CONTINUOUS EMISION MONITORING SYSTEM \(CEMS\)|DEH SYSTEM|FURNACE FLAME MONITORING|GENERATOR HYDROGEN \(H2\) PURITY MONITORING CIRCUIT|INDUCED DRAFT FAN FAULT DIAGNOSIS|PARTIAL DISCHAGRE ONLINE MONITORING|SHUT DOWN BOILER PROTECT EQUIPMENT)$~',
                '~^(?:ANALYZER OF SAMPLING RACK SYSTEM|H2 PURITY ANALYZER BOX|GAS LEAKAGE DETECTOR|METAL DETECTOR [AB]|WATER/COAL/OIL QUALITY INSTRUMENT)$~',
            ],
            'part-piping' => [
                '~^(?:BOILER TUBES OF START UP BOILER|ECONOMIZER TUBES|REHEATER TUBES|SUPERHEATER TUBES|WALL / FURNACE TUBES)$~',
                '~^(?:GENERATOR H2 SUPPLY MANIFOLD \(FROM H2 GAS VESSEL/CYLINDER\)|HYDROGEN MANIFOLD FOR GENERATOR COOLING)$~',
                '~^(?:FLUE GAS DUCTING AND DAMPER|(?:HVAC|PRIMARY AIR|SECONDARY AIR) DUCTING & DAMPER)$~',
                '~^PIPING & VALVE (?:F/F (?:ASH HANDLING & COAL HANDLING|BOILER|BOP|TURBINE) AREA|FOR (?:DESTILATE|DOSING|STEAM) MED|OF (?:CHEMICALS SUPPLY \(DOSING\) FOR CONDENSATE POLISHING PLANT|CHILLED WATER|CHLORINE PLANT|GLAND STEAM SYSTEM|HP HEATER DRAINS|LP HEATER DRAINS|OPEN CYCLE COOLING WATER SYSTEM|REGENERATION FOR CONDENSATE POLISHING PLANT|TURBINE DRAIN SYSTEM)|PRIMARY & SECONDARY DESUPERHEATER SUPERHEATER SPRAY|REHEAT DESUPERHEATER|SUPPLY HEADER H2 PLANT)$~',
                '~^PIPING & VALVES (?:FOR MED (?:EVAPORATION SYSTEM|MIXBED)|FOR SEA WATER MED|IN FIRE PUMP HOUSE|OF (?:AUXILIARY STEAM SYSTEM|BOILER DRAINS & VENT SYSTEM|COLD REHEAT STEAM SYSTEM|EH OIL SYSTEM FOR (?:BFPT|TURBINE)|EXTRACTION STEAM SYSTEM FOR (?:BFPT & DEAERATOR|HP FEEDWATER HEATER|LP FEEDWATER HEATER)|FEEDWATER SYSTEM|HOT REHEAT STEAM SYSTEM|LUBE OIL FOR TURBINE|MAIN STEAM SYSTEM|MED COMPRESSED AIR|MICRO OIL BURNER SYSTEM|POTABLE WATER|SAMPLING RACK SYSTEM))$~',
                '~^PIPING, VALVES & ASSESORIES FOR FOAM SYSTEM$~',
                '~^(?:ASH CONTAINING AERATION|CCCW|CONDENSATE POLISHING PLANT|DOWNCOMER|FLAME MONITORS COOLING|FUEL OIL(?: SYSTEM)?|INSTRUMENT AIR(?: DISTRIBUTION| GENERATING)?|MAIN CONDENSATE|SEALING AIR|SERVICE AIR(?: DISTRIBUTION| GENERATING)?|SERVICE WATER|SOOTBLOWER|STANDBY CONDENSATE DISTRIBUTION) PIPING (?:& VALVES?|VALVE)(?: UNIT)?$~',
                '~^HP BYPASS PIPING (?:&|AND) VALVE OF MAIN STEAM$~',
                '~^LP BYPASS PIPING (?:&|AND) VALVE [AB] OF REHEAT STEAM$~',
                '~^START UP BOILER PIPING & VALVE OF (?:FEEDWATER|STEAM)$~',
                '~^DOSING PIPING FOR DEMINERALIZATION PLANT$~',
                '~^COAL PIPE [A-G]$~',
            ],
            'control-cabinet' => [
                '~^PLC (?:ASH HANDLING SYSTEM|CHLORINE PLANT|COAL HANDLING SYSTEM|ECONOMIZER HOPPER|FOR STRE|HYDROGEN \(H2\) PLANT|MED SYSTEM|STARTUP BOILER)$~',
                '~^(?:150KV PACKAGE GIS|UPS UNIT|CATHODIC PROTECTION RECTIFIER FOR CWP (?:PIPE|PUMP A))$~',
                '~^(?:BOILER|TURBINE|STATION SERVICE|ASH HANDLING|COAL HANDLING|ESP|WATER SYSTEM) POWER CENTER [AB]$~',
                '~^110V DC DISTRIBUTION BOARD (?:COAL HANDLING|NORMAL SYSTEM [AB])$~',
                '~^DC DISTRIBUTON BOARD NORMAL SYSTEM 220V$~',
                '~^6 KV STATION SERVICE BOARD [AB]$~',
                '~^EMERGENCY AUXILIARY POWER BOARD [AB]$~',
                '~^(?:EMERGENCY LIGHTING|LIGHTING|MAINTENANCE) BOARD$~',
                '~^SWITCHGEAR 6 KV UNIT BOARD [AB]$~',
                '~^STRE SWITCHGEAR \(RM 6\) MEDIUM VOLTAGE$~',
                '~^STRE (?:INCOMING|OUT GOING) PANEL 10\.5 KV$~',
                '~^STRE MEDIUM VOLTAGE DISTRIBUTION PANEL 10\.5 KV \(JH 8 D\)$~',
                '~^(?:COMMON|WORK) HBT PANEL$~',
                '~^(?:CABINET OF H2 PLANT \(RECTIFIER,MCC,CONTROL\)|CENTER FIRE ALARM CONTROL PANEL \(ON 13\.700 M OF CENTRAL CONTROL ROOM\)|PANEL CONTROL CENTRAL ECONOMIZER HOPPER SWITCHGEAR ROOM|PANEL ECONOMIZER HOPPER|PANEL LOKAL ECONOMIZER HOPPER|FOAM STORAGE TANK ROOM CONTROL BOX)$~',
            ],
            'storage-tank' => [
                '~^RESIN HOPPER \(INCLUDE EJECTOR\) OF CPP REGENERATION$~',
                '~^(?:COAL BUNKER [A-G]|ESP HOPPER ROW [1-4]|HOPPER JUNCTION HOUSE 8[CD]|BOTTOM ASH BIN|STEEL FLY ASH SILO|ECONOMIZER HOPPER|UNDERGROUND HOPPER)$~',
            ],
            'belt-conveyor' => [
                '~^DRAG DRAIN CHAIN CONVEYOR [1-4]$~',
                '~^(?:BELT CONVEYOR 4|BOOM/ STACKING BELT CONVEYOR|TRIPPER BELT CONVEYOR|(?:PRIMARY|SECONDARY) SCRAPPER CONVEYOR) FOR STRE$~',
                '~^(?:SSC \(SUBMERGED SCRAPPER CONVEYOR\)|TRANSFER CONVEYOR \(TC\) 7B)$~',
            ],
            'air-receiver' => [
                '~^COMPRESS AIR TANK A,B & C$~',
                '~^(?:NEUTRALIZATION, REACTION,FLOCCULATION TANK & AGITATOR OF WWTP|SLUDGE ENRICHMENT TANK INCLUDE AGITATOR)$~',
                '~^(?:CCCW EXPANSION TANK|FEEDWATER TANK OF START UP BOILER|EH OIL TANK FOR (?:BFPT|TURBINE)|HYDROGEN STORAGE TANK \(VESSEL\) OF H2 PLANT|ANION RESIN REGENERATION & SAMAEPARATION VESSEL|CATION RESIN REGENERATION & STORAGE VESSEL|STEAM DRUM|DEAERATOR)$~',
            ],
            'heat-exchanger' => [
                '~^(?:CONDENSER [AB]|GLAND STEAM CONDENSER|STEAM HEATER OF PA TO PULVERIZER A)$~',
            ],
            'power-transformer' => [
                '~^ESP [AB] TRANSFORMER-RECTIFIER FIELD [1-4]$~',
                '~^(?:ESP TRANSFORMER [AB]|EXCITATION TRANSFORMER 6900KVA 20/0\.88KV(?: SET)?|STRE DRY TRANS?FORMER 10\.5 KV/ 400 V 1 MVA)$~',
            ],
            'coal-crusher' => [
                '~^ASH CRUSHER$~',
            ],
            'desiccant-air-dryer' => [
                '~^(?:GENERATOR HYDROGEN \(H2\) DRYER|ADSORBING TYPE \(H2\) HYDROGEN DRYER)$~',
            ],
            'part-valve-damper' => [
                '~^GATE AND HEADSTOCK GEAR$~',
                '~^(?:CCOFA & SOFA DAMPER|SECONDARY AIR DAMPER (?:COAL LAYER (?:D, DE & E|F|GG & G)|LAYER (?:AA, A & AB|B & BC|C & CD|D & DE|E & EF|F & FG|G & GG)))$~',
                '~^TURBINE VALVE$~',
            ],
            'water-pump' => [
                '~^START UP BFP$~',
            ],
            'sootblower' => [
                '~^(?:AIR HEATER SOOTBLOWER|LONG RETRACTABLE SOOTBLOWER (?:LEFT|RIGHT) SIDE|SHORT RETRACTABLE SOOTBLOWER [A-E])$~',
            ],
            'steam-turbine' => [
                '~^(?:BOILER FEED PUMP TURBINE \(BFPT\) [AB]|HIP TURBINE|LP [12] TURBINE)$~',
            ],
            'process-filter' => [
                '~^(?:HIGH FLOW RATE MIXED BED [ABC] OF CPP SYSTEM|MIXED BED [AB])$~',
                '~^(?:AUTOMATIC WASHING FILTER [AB] OF CHLORINE PLANT|DEBRIS FILTER CW PIPE TO CONDENSER [AB]|ELECTRIC FILTER OPEN COOLING WATER|SEAWATER PREFILTER OF CHLORINE PLANT)$~',
            ],
            'truck' => [
                '~^(?:DUMP TRUCK \(HINO\) 0[1-4]|FIRE TRUCK A \(HOWO\) \(SAFETY\)|FIRE TRUCK B \(HINO\)|FIRE TRUCK B \(ZIEGLER TLF40/100-10\)|VACUUM TRUCK)$~',
            ],
            'excavator' => [
                '~^(?:EXCAVATOR A \(CATERPILLAR 320\)|EXCAVATOR B \(VOLVO EC210B\))$~',
            ],
            'forklift' => [
                '~^FORKLIFT (?:[AB]|CAT 10 T)$~',
            ],
            'loader' => [
                '~^(?:SKID STEER LOADER(?: A)? \(SSL CATERPILLAR 226B3\)|WHEEL LOADER A \(LIU GONG S/N [A-Z0-9]{1,32}\)|WHELL LOADER B \(CATERPILLAR 980H\))$~',
            ],
            'dozer' => [
                '~^TRACK DOZER (?:C \(CATERPILLAR D8R 01\)|D \(CATERPILLAR D8R 02\)|E \(CATERPILLAR D8R 03\)|F \(CATERPILLAR D8R 04\))$~',
            ],
        ];

        foreach ($patterns as $family => $familyPatterns) {
            foreach ($familyPatterns as $pattern) {
                if (preg_match($pattern, $name)) {
                    return $family;
                }
            }
        }

        return null;
    }

    private function partFamily(string $description): ?string
    {
        // Whole observed instrument contexts, not a PUMP/MOTOR/BEARING keyword.
        // Spelling variants reflect source text; they do not alter source data.
        if (preg_match('/^TDBFP [AB] (?:BP (?:MOTOR (?:BEARING|WINDING)|RADIAL BEARING)|INLET SIDE (?:LOWER|UPPER) BODY|MECHANICAL SEAL WATER INLET|RADIAL BEARING|THURST BEARING) TEMPERATURE RTD ?[1-6]$/', $description)
            || preg_match('/^BFPT [AB] LUBE OIL (?:FILTER INLET|TANK) TEMPERATURE THERMOCOUPLE$/', $description)) {
            return 'part-temperature-sensor';
        }

        if (preg_match('/^BFPT [AB] (?:ACCUMULATOR|CONTROL OIL FILTER (?:INLET|OUTLET)|EOP OUTLET|JACKING OIL PUMP [AB] OUTLET|LUBE OIL COOLER INLET|LUBE OIL FILTER (?:INLET|OUTLET)|LUBE OIL|LUBE OIL TANK|NO\. ?[12] MOP OUTLET|NO\. ?[12] BEARING INLET OIL|OIL STATION LUBE OIL OUTLET|THRUST BEARING INLET OIL|TURNING GEAR OIL) (?:PRESSURE|PRESSSURE) GAUGE$/', $description)
            || preg_match('/^(?:BFPT [AB] (?:BEARING OIL RETURN TEMPERATURE \((?:BACKWARD|FORWARD)\)|LUBE OIL COOLER (?:INLET|OUTLET) TEMPERATURE|LUBE OIL FILTER INLET TEMPERATURE|OIL COOLER [AB] WATER (?:INLET|RETURN) TEMPERATURE)|TDBFP [AB] NO\. [34] BEARING OIL RETURN TEMPERATURE) THERMOMETER$/', $description)) {
            return 'part-dial-gauge';
        }

        if (preg_match('/^BFPT [AB] (?:(?:CONTROL OIL|LUBE OIL) STRAINER DIFFERENTIAL PRESSURE SWITCH|LUBE OIL HEADER PRESSURE SWITCH L|LUBE OIL PRESSURE SWITCH (?:L|LL \([1-3]\)|LLL)|LUBE OIL TANK LEVEL SWITCH)$/', $description)) {
            return 'part-industrial-switch';
        }

        if (preg_match('/^(?:BFPT A GLAND SEAL STEAM|BFPT [AB] (?:INLET|LUBE OIL)) PRESSURE TRANSMITTER$/', $description)
            || $description === 'ES 4 TO BFPT STEAM FLOW TRANSMITTER') {
            return 'part-transmitter';
        }

        if (preg_match('/^MOTOR CONTROL VALVE (?:COLD|HOT) PRIMARY AIR DAMPER TO MILL [AB]$/', $description)
            || preg_match('/^PNEUMATIC OPERATE VALVE (?:COLD|HOT) PRIMARY AIR TO MILL A$/', $description)) {
            return 'part-valve-damper';
        }

        if (preg_match('/^SEAL AIR PIPING PULVERIZER \(MILL\) [AB]$/', $description)) {
            return 'part-piping';
        }

        return null;
    }

    private function isExplicitGenericPump(string $description): bool
    {
        $name = preg_replace('/^\[E\]\s*/', '', $description);

        // Generic pump visual, without implying water service or internal subtype.
        return (bool) preg_match('/^(?:EH PUMP [AB] FOR (?:BFPT|TURBINE)|RECYCLING PUMP|REGENERATION SPECIAL PUMP [AB])$/', $name);
    }

    private function isExplicitWastewaterPump(string $description): bool
    {
        $name = preg_replace('/^\[E\]\s*/', '', $description);

        // Narrow whole-name FOR exceptions only. Prefixes, parts, combined
        // equipment and different destinations still fail the ordinary guard.
        return (bool) preg_match('/^(?:WASTE WATER PUMP [AB] USED FOR CPP REGENERATION|WASTE WATER PUMP FOR STORAGE POND WWTP)$/', $name);
    }

    private function isExplicitCabinet(string $description): bool
    {
        $name = preg_replace('/^\[E\]\s*/', '', $description);

        // These whole names identify the cabinet/panel as the subject. This is a
        // narrow exception, not permission to strip arbitrary FOR clauses.
        return (bool) preg_match('/^(?:ESP [AB] HIGH VOLTAGE \(HV\) CONTROL CABINET FIELD [1-4]|DCS SERVER CABINET SYSTEM [1-3]|GENERATOR TRANSFORMER UNIT ENERGY METER PANEL|GENERATOR GAS LEAKAGE DETECTION PROCESSOR PANEL|DCS CABINET FOR ESP SYSTEM|HVAC PLC PANEL FOR CENTRAL CONTROL BUILDING|TV CONTROL PANEL FOR FURNACE AND DRUM)$/', $name);
    }
}

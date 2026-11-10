@php
    // Visual placeholders from the user-provided overview, never source identities or measurements.
    $mills = ['G', 'F', 'E', 'D', 'C', 'B', 'A'];
    $millWellness = ['unknown', 'good', 'watch', 'high', 'good', 'good', 'unknown'];
    $wellnessLabels = ['unknown' => '?', 'good' => 'Baik', 'watch' => 'Perhatian', 'high' => 'Tinggi'];
@endphp
<section class="ops-draft" aria-labelledby="ops-overview-title" data-operations-draft>
    <div class="ops-draft-toolbar">
        <span class="ops-toolbar-hint">Pilih simbol untuk detail draft · belum tertaut ke Asset</span>
        <label class="ops-demo-toggle"><input type="checkbox" id="ops-wellness-demo"><span>Contoh warna wellness</span></label>
    </div>
    <div class="ops-overview-heading">
        <div><p class="ops-kicker">PROCESS OVERVIEW / DRAFT 01</p><h2 id="ops-overview-title">Boiler overview</h2></div>
        <div class="ops-source-state"><span class="ops-status-dot"></span><strong>Historian belum terhubung</strong><span>Nilai: Belum terhubung · Link Asset belum dipetakan</span></div>
    </div>
    <div class="ops-metrics" aria-label="Placeholder parameter utama">
        @foreach([['Beban unit', 'MW'], ['Main steam flow', 't/h'], ['Main steam pressure', 'MPa'], ['Main steam temperature', '°C'], ['Drum level', 'mm'], ['Furnace pressure', 'Pa']] as [$label, $unitLabel])
            <div><span>{{ $label }}</span><strong>— <small>{{ $unitLabel }}</small></strong></div>
        @endforeach
    </div>
    <div class="ops-canvas-note"><span>Susunan mengikuti referensi DCS. Identitas asset dan jalur proses belum diverifikasi.</span><strong class="ops-demo-off">Wellness: belum dinilai</strong><strong class="ops-demo-on">SIMULASI WARNA · bukan kondisi aset</strong></div>
    <p class="ops-scroll-hint">↔ Geser diagram untuk melihat seluruh proses.</p>
    <div class="ops-canvas-scroll" role="region" tabindex="0" aria-label="Diagram boiler draft, geser horizontal pada layar kecil">
    <svg class="ops-process" viewBox="0 0 1280 680" xmlns="http://www.w3.org/2000/svg" aria-labelledby="ops-svg-title ops-svg-desc" role="img">
        <title id="ops-svg-title">Draft diagram Boiler overview</title>
        <desc id="ops-svg-desc">Mill G sampai A di kiri, boiler dan drum di tengah, fan dan feedwater di kanan, mengikuti foto referensi. Semua angka masih kosong, status operasi unknown, pemetaan Asset belum tersedia. Simbol membuka detail draft visual. Warna contoh hanya untuk pratinjau Asset Wellness.</desc>
        <defs>
            <pattern id="ops-grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".65" fill="#c8d2d7" opacity=".42"/></pattern>
            <marker id="ops-arrow" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 1 7 4 1 7" fill="none" stroke="context-stroke" stroke-width="1.3"/></marker>
            <g id="ops-valve"><path d="M-8-6 8 6V-6L-8 6Z"/><path d="M0-6V-13M-4-13H4" fill="none"/></g>
            <g id="ops-fan"><circle r="23" class="ops-equipment-body"/><path d="M-12 0H12M4-8 12 0 4 8" class="ops-symbol-line"/></g>
            <g id="ops-pump"><circle r="19" class="ops-equipment-body"/><path d="m-7 9 7-17 7 17M-10 9H10" class="ops-symbol-line"/></g>
        </defs>
        <rect width="1280" height="680" fill="url(#ops-grid)"/>
        <path class="ops-zone-rule" d="M422 38V650M858 38V650"/>
        <text x="26" y="25" class="ops-zone-title">01 / COAL &amp; MILL</text>
        <text x="450" y="25" class="ops-zone-title">02 / BOILER &amp; STEAM</text>
        <text x="890" y="25" class="ops-zone-title">03 / AIR &amp; FLUE GAS</text>
        <g class="ops-pipe ops-coal">
            @foreach($mills as $i => $mill)
                <path d="M338 {{ 84 + $i * 86 }} H{{ 430 + $i * 8 }} V{{ 217 + $i * 61 }} H492"/>
            @endforeach
        </g>
        @foreach($mills as $i => $mill)
            @php($y = 62 + $i * 86)
            <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => 'mill-'.strtolower($mill)])) }}#ops-component-detail" data-component="{{ 'mill-'.strtolower($mill) }}" transform="translate(0 {{ $y }})" class="ops-equipment ops-wellness-{{ $millWellness[$i] }} {{ $draftComponent === 'mill-'.strtolower($mill) ? 'ops-component-selected' : '' }}" aria-label="MILL {{ $mill }}, buka detail draft">
                <title>MILL {{ $mill }} · Placeholder, belum dipetakan ke asset. Operasi unknown. Wellness belum dinilai.</title>
                <path d="M26 34H171M26 58H149V45H171" class="ops-pipe ops-air" marker-start="url(#ops-arrow)"/>
                <use href="#ops-valve" transform="translate(64 34)" class="ops-small-valve"/>
                <use href="#ops-valve" transform="translate(113 58)" class="ops-small-valve"/>
                <text x="80" y="24" class="ops-value">— <tspan class="ops-unit">%</tspan></text>
                <text x="80" y="78" class="ops-value">— <tspan class="ops-unit">%</tspan></text>
                <rect x="177" y="0" width="96" height="13" rx="6" class="ops-feeder"/>
                @foreach([190, 213, 236, 259] as $cx)<circle cx="{{ $cx }}" cy="6.5" r="3.2" class="ops-roller"/>@endforeach
                <path d="M223 13V21" class="ops-pipe"/>
                <path d="M170 22H280V38L260 47V58H195V47L170 38Z" class="ops-equipment-body"/>
                <text x="225" y="42" text-anchor="middle" class="ops-asset-name">MILL {{ $mill }}</text>
                <circle cx="317" cy="35" r="20" class="ops-equipment-body"/>
                <path d="m311 29 12 6-12 6Z" class="ops-symbol-line"/>
                <path d="M280 35H297" class="ops-pipe"/>
                <text x="285" y="3" class="ops-value">— <tspan class="ops-unit">t/h</tspan></text>
                <text x="296" y="72" class="ops-value">— <tspan class="ops-unit">A</tspan></text>
                <text x="175" y="75" class="ops-wellness-default">W: Belum dinilai</text>
                <text x="175" y="75" class="ops-wellness-sample">W: {{ $wellnessLabels[$millWellness[$i]] }} · contoh</text>
                <text x="352" y="40" class="ops-unknown">?</text>
            </a>
        @endforeach
        <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => 'drum'])) }}#ops-component-detail" data-component="{{ 'drum' }}" class="ops-equipment ops-wellness-good {{ $draftComponent === 'drum' ? 'ops-component-selected' : '' }}" aria-label="Drum, buka detail draft">
            <title>DRUM · Pemetaan Asset belum tersedia. Buka detail draft visual. Semua nilai adalah placeholder.</title>
            <text x="548" y="55" class="ops-asset-name">DRUM</text><text x="641" y="55" class="ops-value">— <tspan class="ops-unit">MPa</tspan></text>
            <rect x="547" y="68" width="235" height="45" rx="22" class="ops-equipment-body"/>
            <path d="M569 70V111M759 70V111" class="ops-symbol-line"/>
            <path d="M580 94H748" class="ops-drum-level"/>
            <text x="577" y="132" class="ops-value">— <tspan class="ops-unit">mm</tspan></text><text x="703" y="132" class="ops-value">— <tspan class="ops-unit">mm</tspan></text>
        </a>
        <g class="ops-pipe ops-steam">
            <path d="M576 194V154H472" marker-end="url(#ops-arrow)"/>
            <path d="M627 194V154H820" marker-end="url(#ops-arrow)"/>
            <path d="M577 68V39H501"/>
        </g>
        <text x="465" y="143" class="ops-small-label">IP / — MPa</text><text x="713" y="143" class="ops-small-label">HP / — MPa</text>
        <text x="475" y="176" class="ops-value">— <tspan class="ops-unit">°C</tspan></text><text x="735" y="176" class="ops-value">— <tspan class="ops-unit">°C</tspan></text>
        <path d="M492 194H684V343H770V401H684V607L653 646H519L492 607Z" class="ops-furnace"/>
        <path d="M503 203H674V342M503 600 526 634H647L674 600" class="ops-furnace-inner"/>
        <text x="589" y="216" text-anchor="middle" class="ops-asset-name">FURNACE</text>
        <text x="589" y="234" text-anchor="middle" class="ops-small-label">— Pa · — °C</text>
        @foreach(['G', 'FG', 'F', 'EF', 'E', 'D', 'CD', 'C', 'B', 'AB', 'A'] as $i => $burner)
            @php($by = 261 + $i * 34)
            <g><rect x="527" y="{{ $by - 12 }}" width="119" height="23" rx="3" class="{{ strlen($burner) > 1 ? 'ops-burner-secondary' : 'ops-burner' }}"/>
                <text x="586" y="{{ $by + 4 }}" text-anchor="middle" class="ops-small-label">{{ $burner }}</text>
                @foreach([527, 646] as $bx)<circle cx="{{ $bx }}" cy="{{ $by }}" r="5" class="ops-burner-port"/>@endforeach
            </g>
        @endforeach
        <text x="589" y="663" text-anchor="middle" class="ops-small-label">Burner status: unknown</text>
        <path d="M684 294 747 270H828V349L802 374H770" class="ops-furnace"/>
        <path d="M747 270 828 318M828 270 747 318M747 318H828" class="ops-symbol-line"/>
        <text x="788" y="259" text-anchor="middle" class="ops-value">— <tspan class="ops-unit">Pa</tspan></text>
        <text x="788" y="339" text-anchor="middle" class="ops-small-label">ECONOMIZER</text>
        <text x="788" y="391" text-anchor="middle" class="ops-value">— <tspan class="ops-unit">°C</tspan></text>
        <g class="ops-pipe ops-water"><path d="M782 91H843V423H745V374" marker-end="url(#ops-arrow)"/></g>
        <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => 'scan-fan'])) }}#ops-component-detail" data-component="{{ 'scan-fan' }}" class="ops-equipment ops-wellness-unknown {{ $draftComponent === 'scan-fan' ? 'ops-component-selected' : '' }}" aria-label="Scan fan A dan B, buka detail draft">
            <title>SCAN FAN A / B · Operasi unknown. Pemetaan Asset belum tersedia. Buka detail draft visual.</title>
            <text x="755" y="465" text-anchor="middle" class="ops-small-label">SCAN FAN</text>
            @foreach([['A', 503], ['B', 578]] as [$fan, $fy])
                <use href="#ops-fan" transform="translate(755 {{ $fy }})"/>
                <path d="M731 {{ $fy }}H706" class="ops-pipe ops-air"/>
                <text x="715" y="{{ $fy + 5 }}" class="ops-small-label">{{ $fan }}</text>
                <text x="755" y="{{ $fy + 39 }}" text-anchor="middle" class="ops-value">— <tspan class="ops-unit">kPa</tspan></text>
            @endforeach
        </a>
        <g class="ops-pipe ops-air">
            <path d="M939 101V354H869" marker-end="url(#ops-arrow)"/>
            <path d="M1142 101V370H869" marker-end="url(#ops-arrow)"/>
            <path d="M986 284V337H869" marker-end="url(#ops-arrow)"/>
            <path d="M1095 284V321H869" marker-end="url(#ops-arrow)"/>
        </g>
        <g class="ops-pipe ops-flue"><path d="M828 298H1039V214M986 184V160H1039V93M1095 184V160H1039" marker-end="url(#ops-arrow)"/></g>
        <path d="M1027 141V61H1052V141M1027 73H1052M1027 88H1052" class="ops-stack"/>
        <text x="1040" y="51" text-anchor="middle" class="ops-small-label">STACK</text>
        @foreach([
            ['PAF A', 939, 101, 'watch'], ['PAF B', 1142, 101, 'good'],
            ['IDF A', 986, 204, 'good'], ['IDF B', 1095, 204, 'high'],
            ['FDF A', 986, 284, 'good'], ['FDF B', 1095, 284, 'unknown'],
        ] as [$fan, $fx, $fy, $wellness])
            <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => strtolower(str_replace(' ', '-', $fan))])) }}#ops-component-detail" data-component="{{ strtolower(str_replace(' ', '-', $fan)) }}" class="ops-equipment ops-wellness-{{ $wellness }} {{ $draftComponent === strtolower(str_replace(' ', '-', $fan)) ? 'ops-component-selected' : '' }}" aria-label="{{ $fan }}, buka detail draft">
                <title>{{ $fan }} · Operasi unknown. Wellness belum dinilai. Pemetaan Asset belum tersedia. Buka detail draft visual.</title>
                <use href="#ops-fan" transform="translate({{ $fx }} {{ $fy }})"/>
                <text x="{{ $fx }}" y="{{ $fy - 32 }}" text-anchor="middle" class="ops-asset-name">{{ $fan }}</text>
                <text x="{{ $fx + ($fx < 1040 ? -38 : 38) }}" y="{{ $fy + 5 }}" text-anchor="{{ $fx < 1040 ? 'end' : 'start' }}" class="ops-value">— <tspan class="ops-unit">A</tspan></text>
            </a>
        @endforeach
        <rect x="963" y="320" width="46" height="18" rx="3" class="ops-heat-exchanger"/><text x="986" y="333" text-anchor="middle" class="ops-small-label">APH A</text>
        <rect x="1072" y="304" width="46" height="18" rx="3" class="ops-heat-exchanger"/><text x="1095" y="317" text-anchor="middle" class="ops-small-label">APH B</text>
        <text x="890" y="411" class="ops-zone-title">04 / FEEDWATER</text>
        <g class="ops-pipe ops-water"><path d="M1240 453H843M1030 492V453M1120 492V453M1210 492V453" marker-end="url(#ops-arrow)"/></g>
        <rect x="890" y="438" width="59" height="30" rx="13" class="ops-heat-exchanger"/><path d="m901 453 7-7 13 14 13-14 7 7" class="ops-pipe ops-steam"/>
        <text x="920" y="431" text-anchor="middle" class="ops-small-label">HPH</text>
        @foreach([['BFP B',1030,'good'], ['BFP A',1120,'watch'], ['BFSP',1210,'unknown']] as [$pump,$px,$wellness])
            <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => strtolower(str_replace(' ', '-', $pump))])) }}#ops-component-detail" data-component="{{ strtolower(str_replace(' ', '-', $pump)) }}" class="ops-equipment ops-wellness-{{ $wellness }} {{ $draftComponent === strtolower(str_replace(' ', '-', $pump)) ? 'ops-component-selected' : '' }}" aria-label="{{ $pump }}, buka detail draft">
                <title>{{ $pump }} · Pemetaan Asset belum tersedia. Buka detail draft visual. Operasi unknown.</title>
                <use href="#ops-valve" transform="translate({{ $px }} 453)" class="ops-small-valve"/>
                <use href="#ops-pump" transform="translate({{ $px }} 505)"/>
                <text x="{{ $px }}" y="433" text-anchor="middle" class="ops-value">— <tspan class="ops-unit">%</tspan></text>
                <text x="{{ $px }}" y="541" text-anchor="middle" class="ops-asset-name">{{ $pump }}</text>
                <text x="{{ $px }}" y="559" text-anchor="middle" class="ops-value">— <tspan class="ops-unit">A</tspan></text>
            </a>
        @endforeach
        <text x="898" y="494" class="ops-value">— <tspan class="ops-unit">t/h</tspan></text>
        <text x="890" y="599" class="ops-zone-title">05 / FUEL OIL</text>
        <g class="ops-pipe ops-oil"><path d="M1240 625H885" marker-end="url(#ops-arrow)"/><path d="M885 654H1240" marker-end="url(#ops-arrow)"/></g>
        @foreach([950,1060,1170] as $vx)<use href="#ops-valve" transform="translate({{ $vx }} 625)" class="ops-small-valve"/><use href="#ops-valve" transform="translate({{ $vx }} 654)" class="ops-small-valve"/>@endforeach
        <text x="1110" y="618" class="ops-small-label">OIL SUPPLY · — t/h</text><text x="1110" y="674" class="ops-small-label">RETURN OIL · — t/h</text>
    </svg>
    </div>
    <details class="ops-component-directory">
        <summary>Daftar komponen draft · {{ count($components) }} simbol</summary>
        <p>Label dari gambar, bukan identitas Asset. Detail hanya menampilkan placeholder.</p>
        <nav aria-label="Detail komponen BOIL">
            @foreach($components as $componentId => $item)
                <a href="{{ route('operations', array_merge($contextQuery, ['screen' => 'BOIL', 'component' => $componentId])) }}#ops-component-detail" @if($draftComponent === $componentId) aria-current="true" @endif>{{ $item['label'] }}</a>
            @endforeach
        </nav>
    </details>
    <div class="ops-legend">
        <div class="ops-wellness-legend"><strong>Asset Wellness <small>Legenda konsep</small></strong><span><i class="good"></i>Baik</span><span><i class="watch"></i>Perlu perhatian</span><span><i class="high"></i>Prioritas tinggi</span><span><i class="unknown"></i>Belum dinilai</span></div>
        <div class="ops-state-legend"><span>Operasi <b>? Unknown</b></span><span>Alarm DCS <b>Tidak terhubung</b></span></div>
    </div>
    <div class="ops-footnote"><span><b>—</b> Nilai kosong, bukan nol · Waktu sumber: — · Kualitas: unknown</span><span>Warna jalur = media proses, bukan status asset.</span></div>
</section>

@props(['variant' => 'inventory'])
{{-- Decorative category art only: never a reading, source photo, chart or status indicator. --}}
<svg {{ $attributes->class(['card-motif']) }} viewBox="0 0 112 88" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path class="card-motif-base" d="M12 72h88" />
    @switch($variant)
        @case('records')
            <rect class="card-motif-surface" x="35" y="12" width="48" height="56" rx="5" />
            <rect class="card-motif-surface" x="23" y="21" width="48" height="55" rx="5" />
            <path d="M35 35h24M35 44h24M35 53h18M35 65h10" />
            <path class="card-motif-detail" d="M82 25h9m-9 9h6M16 49h-5m5 9h-3" />
            @break
        @case('measurement')
            <rect class="card-motif-surface" x="27" y="14" width="43" height="61" rx="7" />
            <rect x="35" y="23" width="27" height="20" rx="3" />
            <path d="M42 31h13M42 36h8M38 66h20M38 52h4m7 0h4m7 0h1" />
            <path d="M70 57h7a9 9 0 0 0 9-9V30m-4 0h8V18h-8z" />
            <path class="card-motif-detail" d="M20 24h-7m7 9h-4M80 67h12" />
            @break
        @case('inspection')
            <rect class="card-motif-surface" x="23" y="17" width="48" height="57" rx="5" />
            <path class="card-motif-surface" d="M37 17v-5h20v5m-20 0h20" />
            <path d="M34 31h24M34 40h18M34 50h10M34 59h13" />
            <circle class="card-motif-surface" cx="74" cy="53" r="14" />
            <path d="m84 64 12 12M69 53h10m-5-5v10" />
            <path class="card-motif-detail" d="M82 24h9m-9 8h5M16 54h-5" />
            @break
        @default
            <path class="card-motif-surface" d="m24 22 33-10 29 9v49l-33 8-29-9z" />
            <path d="m24 22 29 8 33-9M53 30v48M61 39l17-4v25l-17 4zM31 33l13 4v23l-13-4z" />
            <path d="m65 44 8-2m-8 9 8-2M35 43l5 2m-5 6 5 2M35 65l7 2M63 70l12-3" />
            <path class="card-motif-detail" d="M94 32h7m-7 9h4M14 49H9m5 9h-3" />
    @endswitch
</svg>

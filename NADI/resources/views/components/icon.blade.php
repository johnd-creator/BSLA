@props(['name'])
<svg {{ $attributes->class(['icon']) }} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    @switch($name)
        @case('home')
            <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" />
            @break
        @case('asset')
            <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
            @break
        @case('operations')
            <rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8m-4-4v4M6 11h3l2-4 3 7 2-3h2" />
            @break
        @case('inspection')
            <rect x="5" y="5" width="14" height="16" rx="2" /><rect x="9" y="3" width="6" height="4" rx="1" /><path d="m9 13 2 2 4-4M9 18h6" />
            @break
        @case('users')
            <circle cx="9" cy="8" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-16a3 3 0 0 1 0 6m3 10v-3a6 6 0 0 0-2-4" />
            @break
        @case('access')
            <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Zm-4 9 3 3 5-6" />
            @break
        @case('logout')
            <path d="M9 5H5v14h4m5-14 7 7-7 7m-5-7h12" />
            @break
        @case('chevron')
            <path d="m8 10 4 4 4-4" />
            @break
    @endswitch
</svg>

@props(['filters' => []])
@if(collect($filters)->keys()->contains(fn ($key) => request()->filled($key)))
    <div class="active-filters" aria-label="Filter aktif">
        <span>Filter aktif</span>
        @foreach($filters as $key => $label)
            @if(request()->filled($key))
                <a class="filter-chip" href="{{ request()->fullUrlWithoutQuery([$key, 'offset', 'page', 'activity_page']) }}" aria-label="Hapus filter {{ $label }}: {{ request($key) }}">
                    {{ $label }}: <strong>{{ request($key) }}</strong><span aria-hidden="true">×</span>
                </a>
            @endif
        @endforeach
    </div>
@endif

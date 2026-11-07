<nav class="overview-tabs" aria-label="Ringkasan dan data">
    @foreach(['home' => 'Overview', 'data-quality' => 'Kualitas data', 'reports.index' => 'Laporan'] as $name => $label)
        <a href="{{ route($name) }}" @if(request()->routeIs($name)) aria-current="page" @endif>{{ $label }}</a>
    @endforeach
</nav>

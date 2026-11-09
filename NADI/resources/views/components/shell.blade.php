@props(['title', 'eyebrow' => null])
<x-page :title="$title">
    <a class="skip-link" href="#content">Lewati ke konten</a>
    <div class="workspace">
        <aside class="sidebar" aria-label="Navigasi utama">
            <a class="brand" href="{{ route('home') }}" aria-label="NADI Beranda"><x-brand /></a>
            <details class="navigation" open>
                <summary><x-icon name="menu" /><span>Menu navigasi</span></summary>
                <div class="navigation-body">
                    <nav aria-label="Menu workspace">
                        <div class="nav-label">WORKSPACE</div>
                        <a href="{{ route('home') }}" @class(['nav-link', 'selected' => request()->routeIs('home')]) @if(request()->routeIs('home')) aria-current="page" @endif><x-icon name="home" />Beranda</a>
                        <details class="asset-menu" @if(request()->routeIs('assets.*', 'work-orders.*', 'disruptions.*', 'priorities.*', 'action-board')) open @endif>
                            <summary class="nav-link"><x-icon name="asset" />Asset <x-icon name="chevron" class="menu-chevron" /></summary>
                            <div class="asset-submenu">
                                <a href="{{ route('assets.index') }}" @class(['nav-link', 'selected' => request()->routeIs('assets.*')]) @if(request()->routeIs('assets.*')) aria-current="page" @endif>Master Asset</a>
                                <a href="{{ route('work-orders.index') }}" @class(['nav-link', 'selected' => request()->routeIs('work-orders.*')]) @if(request()->routeIs('work-orders.*')) aria-current="page" @endif>Work Orders</a>
                                <a href="{{ route('disruptions.index') }}" @class(['nav-link', 'selected' => request()->routeIs('disruptions.*')]) @if(request()->routeIs('disruptions.*')) aria-current="page" @endif>Log Gangguan Aset</a>
                                <a href="{{ route('action-board') }}" @class(['nav-link', 'selected' => request()->routeIs('action-board', 'priorities.*')]) @if(request()->routeIs('action-board', 'priorities.*')) aria-current="page" @endif>Action Board</a>
                            </div>
                        </details>
                        <details class="asset-menu" @if(request()->routeIs('operations', 'operations.*')) open @endif>
                            <summary class="nav-link"><x-icon name="operations" />Operasi <x-icon name="chevron" class="menu-chevron" /></summary>
                            <div class="asset-submenu">
                                <a href="{{ route('operations') }}" @class(['nav-link', 'selected' => request()->routeIs('operations')]) @if(request()->routeIs('operations')) aria-current="page" @endif>Konteks operasi <small class="nav-draft">Draft</small></a>
                                <a href="{{ route('operations.historian') }}" @class(['nav-link', 'selected' => request()->routeIs('operations.historian')]) @if(request()->routeIs('operations.historian')) aria-current="page" @endif>Historian <small class="nav-draft">Pondasi</small></a>
                                <a href="{{ route('operations.cems') }}" @class(['nav-link', 'selected' => request()->routeIs('operations.cems')]) @if(request()->routeIs('operations.cems')) aria-current="page" @endif>CEMS</a>
                            </div>
                        </details>
                        <div class="nav-label nav-section">PEMELIHARAAN</div>
                        <a href="{{ route('pdm.index') }}" @class(['nav-link', 'selected' => request()->routeIs('pdm.*')]) @if(request()->routeIs('pdm.*')) aria-current="page" @endif><x-icon name="inspection" />Logbook PdM <small class="nav-draft">Draft</small></a>
                        <a href="{{ route('inspections.index') }}" @class(['nav-link', 'selected' => request()->routeIs('inspections.*')]) @if(request()->routeIs('inspections.*')) aria-current="page" @endif><x-icon name="inspection" />Rekomendasi inspeksi</a>
                        <div class="nav-label nav-section">DATA & LAPORAN</div>
                        <a href="{{ route('wellness.index') }}" @class(['nav-link', 'selected' => request()->routeIs('wellness.*')]) @if(request()->routeIs('wellness.*')) aria-current="page" @endif><x-icon name="asset" />Asset Wellness <small class="nav-draft">Draft</small></a>
                        <a href="{{ route('reliability.index') }}" @class(['nav-link', 'selected' => request()->routeIs('reliability.*')]) @if(request()->routeIs('reliability.*')) aria-current="page" @endif><x-icon name="inspection" />Reliability</a>
                        <a href="{{ route('data-quality') }}" @class(['nav-link', 'selected' => request()->routeIs('data-quality')]) @if(request()->routeIs('data-quality')) aria-current="page" @endif><x-icon name="access" />Kualitas data</a>
                        <a href="{{ route('reports.index') }}" @class(['nav-link', 'selected' => request()->routeIs('reports.*')]) @if(request()->routeIs('reports.*')) aria-current="page" @endif><x-icon name="inspection" />Laporan</a>
                        @can('manage-users')
                            <div class="nav-label administration">ADMINISTRASI</div>
                            <a href="{{ route('users.index') }}" @class(['nav-link', 'selected' => request()->routeIs('users.*')]) @if(request()->routeIs('users.*')) aria-current="page" @endif><x-icon name="users" />User management</a>
                            <a href="{{ route('roles.index') }}" @class(['nav-link', 'selected' => request()->routeIs('roles.*')]) @if(request()->routeIs('roles.*')) aria-current="page" @endif><x-icon name="access" />Role & akses</a>
                        @endcan
                    </nav>
                    <div class="sidebar-bottom"><span class="environment">BSLA · Local development</span></div>
                </div>
            </details>
        </aside>
        <div class="main-area">
            <header class="topbar">
                <div class="topbar-heading">@if($eyebrow)<p class="eyebrow">{{ $eyebrow }}</p>@endif<div class="workspace-title">@unless(request()->routeIs('home'))<a class="workspace-home" href="{{ route('home') }}" aria-label="Kembali ke Beranda">NADI</a><span class="workspace-divider" aria-hidden="true">/</span>@endunless<h1>{{ $title }}</h1></div></div>
                <div class="topbar-actions">
                    <div class="account" aria-label="Akun saat ini">
                        <span class="avatar" aria-hidden="true">{{ mb_substr(auth()->user()->name, 0, 1) }}</span>
                        <div class="account-details"><strong>{{ auth()->user()->name }}</strong><small>{{ implode(' · ', auth()->user()->roles ?? []) }}</small></div>
                    </div>
                    <form class="logout-form" method="post" action="{{ route('logout') }}">
                        @csrf
                        <button class="logout" type="submit"><x-icon name="logout" /><span>Keluar</span></button>
                    </form>
                </div>
            </header>
            <main id="content" class="content" tabindex="-1"><x-feedback />{{ $slot }}</main>
        </div>
    </div>
</x-page>

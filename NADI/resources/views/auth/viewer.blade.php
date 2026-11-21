<x-page title="Viewer">
    <main class="login-main">
        <div class="login-card">
            <h1>Selamat datang di NADI</h1>
            <p>Akun Viewer belum memiliki akses data operasional.</p>
            <form method="post" action="{{ route('logout') }}">
                @csrf
                <button class="button primary" type="submit">Keluar</button>
            </form>
        </div>
    </main>
</x-page>

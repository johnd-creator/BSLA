<x-page title="Masuk direktori internal">
    <main class="login-main">
        <div class="login-card">
            <h1>Masuk dengan direktori internal</h1>
            <p>Untuk akun Viewer. Tidak ada akses data operasional.</p>
            <x-feedback />
            <form method="post" action="{{ route('directory.login.store') }}" class="stack">
                @csrf
                <label for="login">Nama akun direktori</label>
                <input id="login" name="login" value="{{ old('login') }}" autocomplete="username" required maxlength="254">
                <x-field-error name="login" />
                <label for="password">Kata sandi direktori</label>
                <input id="password" type="password" name="password" autocomplete="current-password" required maxlength="256">
                <x-field-error name="password" />
                <button class="button primary" type="submit">Masuk</button>
            </form>
            <p><a href="{{ route('login') }}">Kembali ke akun lokal NADI</a></p>
        </div>
    </main>
</x-page>

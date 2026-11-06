<x-page title="Masuk">
    <div class="login-layout">
        <main class="login-main">
            <a class="brand" href="{{ route('login') }}" aria-label="NADI"><x-brand /></a>
            <div class="login-card">
                <h1>Masuk ke workspace</h1>
                <p class="muted intro">Gunakan akun NADI Anda untuk melanjutkan.</p>
                <x-feedback />
                <form method="post" action="{{ route('login.store') }}" class="stack">
                    @csrf
                    <div>
                        <label for="login">Username atau email</label>
                        <input id="login" type="text" name="login" value="{{ old('login') }}" autocomplete="username" placeholder="Masukkan username atau email" required maxlength="254" autofocus @if($errors->has('login')) aria-invalid="true" @endif>
                    </div>
                    <div>
                        <label for="password">Kata sandi</label>
                        <input id="password" type="password" name="password" autocomplete="current-password" placeholder="Masukkan kata sandi" required maxlength="256">
                    </div>
                    <button class="button primary full" type="submit">Masuk</button>
                </form>
                <p class="login-help">Belum punya akses? Hubungi administrator workspace Anda.</p>
            </div>
            <footer class="login-footer"><span>BSLA</span><span>Local development</span></footer>
        </main>
    </div>
</x-page>

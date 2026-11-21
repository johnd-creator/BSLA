<x-shell title="LDAP / Microsoft AD" eyebrow="PENGATURAN">
    <div class="section-intro">
        <p><span class="badge neutral">Draft saja</span> Nilai di sini tidak mengaktifkan LDAP dan tidak mengubah konfigurasi login yang berjalan.</p>
    </div>
    <section class="panel" aria-labelledby="directory-draft-title">
        <div class="panel-heading"><h2 id="directory-draft-title">Draft koneksi Microsoft AD</h2></div>
        <form method="post" action="{{ route('settings.directory.update') }}" class="stack">
            @csrf
            <div>
                <label for="host">Nama server AD (FQDN)</label>
                <input type="text" id="host" name="host" value="{{ $draft['host'] ?? '' }}" maxlength="253" placeholder="dc01.example.internal" spellcheck="false">
                <x-field-error name="host" />
            </div>
            <p class="muted">Port tetap 636 (LDAPS). Simpan draft tidak mencoba menyambung ke server tersebut.</p>
            <div>
                <label for="base_dn">Base DN</label>
                <input type="text" id="base_dn" name="base_dn" value="{{ $draft['base_dn'] ?? '' }}" maxlength="512" spellcheck="false">
                <x-field-error name="base_dn" />
            </div>
            <div>
                <label for="group_dn">DN grup Viewer yang diizinkan</label>
                <input type="text" id="group_dn" name="group_dn" value="{{ $draft['group_dn'] ?? '' }}" maxlength="512" spellcheck="false">
                <x-field-error name="group_dn" />
            </div>
            <div>
                <label for="bind_name">Username atau DN akun bind (baca saja)</label>
                <input type="text" id="bind_name" name="bind_name" value="{{ $draft['bind_name'] ?? '' }}" maxlength="512" spellcheck="false">
                <x-field-error name="bind_name" />
                <p class="muted">Jangan masukkan kata sandi bind atau token di halaman ini. Pengelola server menyimpannya di konfigurasi rahasia saat pilot disetujui.</p>
            </div>
            <div>
                <label for="current_password">Konfirmasi kata sandi akun lokal NADI</label>
                <input type="password" id="current_password" name="current_password" required maxlength="256" autocomplete="current-password">
                <x-field-error name="current_password" />
            </div>
            <div><button class="button primary" type="submit">Simpan draft</button></div>
        </form>
    </section>
</x-shell>

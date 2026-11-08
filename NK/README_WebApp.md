# NK — dokumentasi consumer independen

NK adalah aplikasi Streamlit prediksi nilai kalor, terpisah dari NADI Laravel.
Direktori publik ini hanya dokumentasi. Implementasi, model/scaler, notebook,
data training dan mapping privat pada checkout terpisah tidak dipublikasikan
oleh pembaruan ini. Lihat [roadmap NK](../plans/NK-ROADMAP.md) dan [AGENTS](AGENTS.md).

Cara kerja: periksa checkout yang benar → edit kecil → uji sesuai dampak →
inspeksi hasil. Jangan membuat worktree/tim/handoff berlapis sebagai default.
NADI aktif dikembangkan di [Laravel](../NADI/README.md); pengembangan NK tidak
mengganti UI, collector, data atau deployment NADI.

## Batas input dan model

- NK tidak memiliki database aplikasi. History berupa session-local yang terbatas.
- Manual/CSV dan stored PI Collector API adalah pilihan eksplisit; tidak ada
  source PI/SQL langsung, credential sumber, collection trigger atau collector baru.
- Pertahankan 13 fitur, urutan training dan pasangan model/scaler. Candidate tag
  bukan mapping; makna, unit dan provenance harus diverifikasi engineer.
- Missing, stale, bad quality, timestamp naive/skew dan nilai non-finite memblokir
  mode otomatis, bukan diganti nol atau manual secara diam-diam.
- PS berarti pemakaian sendiri. Tag/unit W/MW, SFC dan ekuivalensi APH membutuhkan
  evidence, bukan tebakan. Integrasi teknis bukan sertifikasi akurasi model.
- Jangan mempublikasikan data/model atau hasil evaluasi privat sebagai bagian
  docs task. Tidak ada klaim confidence interval/akurasi produksi dalam dokumen ini.

Jalankan pemeriksaan hanya pada checkout yang memang memiliki source/dependencies,
dengan fixture sintetis dan tanpa source produksi. Publication kode/model NK atau
activation runtime memerlukan pekerjaan dan scope tersendiri.

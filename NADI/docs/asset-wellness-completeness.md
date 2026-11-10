# Matriks kelengkapan Asset Wellness

Tambahan lokal 10 November 2026 pada GET `/asset-wellness?asset_ref=…`.
`AssetWellnessCompleteness` membaca rencana, pengukuran, analisis dan review
existing. Tidak ada route tulis, tabel, migrasi, input lapangan atau score baru.

## Penyebut dan waktu

- Satu baris = satu titik/konteks dari rencana PdM **lokal aktif** untuk exact
  asset. Ini belum membuktikan seluruh titik wajib aset/pabrik telah dipetakan.
  Rencana dijeda dikecualikan; jumlahnya tetap disebutkan. Tanpa rencana aktif,
  penyebut belum ditentukan. Storage rencana tidak tersedia berbeda dari nol.
- Matriks adalah keadaan saat dibaca, dengan tanggal Asia/Jakarta, tanpa filter
  periode laporan Wellness. Laporan historis komponen di bawah tetap memiliki
  periodenya sendiri. Matriks bukan kepatuhan masa lalu atau snapshot immutable.
- Maksimal 20 rencana aktif, diurutkan tanggal jatuh tempo pertama lalu ID.
  Total exact asset dan banyak baris diperiksa ditampilkan terpisah. Ringkasan
  berlaku hanya bagi baris yang diperiksa dan dilabel parsial bila terpotong.
  Tautan rencana existing menyediakan pagination seluruh rencana.

## Bukti per titik

- Memakai `PdmSchedule::coverage`, bukan perhitungan coverage yang bersaing:
  routine-only, exact asset/template/fingerprint/snapshot/metode/unit/konteks,
  nilai terisi dan numerik finite bila perlu, waktu bukan masa depan. Nol sah.
  Ini validitas struktural, bukan sertifikasi alat, mapping atau kondisi sehat.
- Seperti jadwal existing, nilai terbaru kosong/tidak cocok dilewati ke bukti
  valid sebelumnya; ini disebutkan jelas. Matriks tidak memakai preview threshold
  Wellness yang memiliki aturan latest-only berbeda. Tidak ada konversi unit.
- Belum diukur, masih berlaku, kedaluwarsa, dan belum pasti dipisahkan. Jatuh
  tempo hari ini, terlambat dan terjadwal memakai interval kalender existing.
  Memundurkan tanggal pertama tidak memperbarui usia pengukuran lama.
- Batas 250 kandidat per rencana tetap berlaku. Bila bukti valid tidak ditemukan
  dan masih ada kandidat lebih lama, hasil unknown, bukan missing atau zero.
  Presisi tanggal saja tetap literal, tanpa jam buatan.
- Analisis terkait pengukuran valid terpilih memakai `pdmReviewState()`:
  belum dianalisis, basis unknown, stale, atau sesuai basis. Analisis aset lain
  tidak dilampirkan. Status current tidak membuktikan diagnosis atau approval.

## Tindak lanjut

Baris titik menautkan rekomendasi pada pengukuran terpilih bila ada. Bagian aset
terpisah juga memuat hingga 20 rekomendasi lokal terakhir menurut `updated_at`
dan ID agar tindak lanjut pada pengukuran lama tidak menghilang ketika ada nilai
baru. Total/parsial disebutkan. Rekomendasi tanpa tautan PdM tetap dibedakan dan
bukan otomatis bukti suatu titik rencana.

Status tindak lanjut dan efektivitas ditampilkan terpisah. **Selesai bukan bukti
efektif.** Review terbaru memakai `ActionEffectiveness::state`, termasuk perubahan
basis rekomendasi, pengukuran sebelum/sesudah dan template. Tanpa review berarti
belum dinilai; tanpa tabel review berarti unavailable. Keputusan tetap penilaian
engineer, bukan kondisi sehat. Tautan menuju pengukuran, analisis, rencana dan
riwayat review existing; tidak ada perubahan status atau request sumber baru.

## Publication verification

See [public-source integration](publication.md) for the checks run against this
publication branch. Historical feature QA is not a fresh browser pass or an
engineering signoff. No source records, private catalogs, runtime data, database
activation, merge or deployment are included in publication.

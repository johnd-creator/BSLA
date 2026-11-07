# Tren PdM per aset dan titik

Implementasi lokal Laravel, 8 November 2026 (WIB). `/pdm/trends` tersedia dari
Logbook PdM, riwayat, detail aktivitas per titik, dan menu detail aset.
Tidak memerlukan migrasi atau impor histori. Database pengguna tetap digunakan
sebagaimana adanya; halaman kosong menyatakan belum ada pengukuran lokal.

## Pemilihan dan kesebandingan

1. Pilih identitas aset persis dari aktivitas lokal, lalu template/konteks dan
   titik numerik. Link detail aktivitas membawa snapshot dan titik yang tepat.
2. Seri hanya membaca asset_ref, template_id, fingerprint, metode, mode,
   alat/laporan, kondisi operasi dan dasar pemilihan/lokasi yang identik.
   Snapshot penuh, definisi titik dan satuan diperiksa lagi per aktivitas.
3. Motor/fan, OLD/NEW, workbook salinan, versi template, parameter, unit dan
   konteks berbeda tidak digabung. Tidak ada konversi unit, fuzzy mapping atau
   anggapan nomor bearing berarti DE/NDE. Konteks identik **bukan** verifikasi
   kesebandingan; pemetaan dan hasil tetap draft belum disahkan.
4. Dropdown memuat 50 konteks terbaru berdasarkan ID aktivitas. Konteks/varian
   unit lain tetap dapat dibuka dari detail aktivitas di riwayat. Grafik dibatasi
   250 aktivitas terbaru dalam konteks yang dipilih dan menampilkan peringatan
   bila histori terpotong. Batas tidak menyiratkan histori sudah lengkap.

## Grafik dan bukti

- Scatter per tanggal kalender sumber, tidak menggunakan timestamp tengah malam
  rekaan. Tanggal saja tetap NULL pada measured_at dan timezone. Catatan berjam
  memakai measured_on sumber, waktu aslinya terlihat di tabel bukti.
- Jarak sumbu X mengikuti selisih hari nyata. Catatan pada tanggal sama dapat
  bertumpuk dan tidak dinyatakan memiliki urutan intrahari. Tidak ada interpolasi,
  penyambung garis, rata-rata, slope, alarm, ambang atau diagnosis otomatis.
- Nilai kosong bukan nol. Nol/negatif yang valid tetap tampil; angka tidak hingga,
  teks, tanggal/konteks tidak lengkap dan template review-only tidak diplot.
  Bukti kosong/tidak valid tetap terlihat, struktur/satuan berbeda dihitung
  sebagai pengecualian. Nilai sangat besar dinormalisasi hanya untuk koordinat SVG
  agar tidak overflow; raw value tidak diubah.
- Satu tanggal tidak memberi perbandingan lintas tanggal; dua tanggal hanya
  memberi perbedaan dua pengukuran. Keduanya berlabel data belum cukup untuk tren
  bermakna. Tiga tanggal atau lebih **tidak** dinyatakan signifikan secara statistik;
  UI meminta tinjauan engineer atas interval, metode dan kondisi.
- Rentang nilai dan jeda terpanjang hanya deskriptif. Jeda antar tanggal terukur
  bukan bukti pengukuran yang terlewat, keterlambatan jadwal atau perubahan kondisi.
- Label rentang nilai dan tanggal memakai HTML 12px di luar SVG agar tidak
  mengecil pada layar HP. Grafik adalah visual noninteraktif; tautan aktivitas
  pada tabel bukti memiliki target sentuh minimal 44px.
- Tabel bukti menghubungkan setiap angka dengan detail draft dan versinya. Panel
  konteks menunjukkan sumber template, sel, fingerprint dan SHA workbook, tanpa
  mengklaim semua nilai berasal dari workbook tersebut.

## Otorisasi dan penyimpanan

Halaman GET read-only mengikuti auth/current-account untuk seluruh empat role
pembaca yang ada. Tidak ada HTTP Mart/source, collector, source write atau
penulisan data dari halaman tren. Pembuatan/edit pengukuran tetap melalui gate
engineer dan validasi PdM lama. Label/angka/catatan di-escape saat dirender.
Tidak ada dependency baru, commit, push, deployment atau perubahan `.env`.

## Verification boundary

Public tests use fictional assets, measurements, in-memory SQLite and mocked HTTP.
They establish software behavior, not source freshness, verified engineering
judgments or deployment acceptance. Private runtime evidence is not shipped.
Run the aggregate checks in the workspace README against the selected commit.

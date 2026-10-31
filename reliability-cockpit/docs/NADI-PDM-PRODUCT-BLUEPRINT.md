# NADI PdM — Product Owner blueprint

31 Oktober 2026 · NADI-PDM-PRODUCT-RESET-01 · **Usulan untuk persetujuan PO**.
Dokumen ini adalah pintu masuk tunggal untuk memahami pekerjaan engineer. Ini bukan izin implementasi, deployment, import, perubahan role, atau persetujuan metode.

## Keputusan produk

NADI membantu engineer menjawab: **pekerjaan untuk aset mana, apa yang diukur, apa bukti sebelumnya, apa analisis manusia, siapa yang mereview, dan apa tindak lanjutnya?**

| Pilar | Manfaat | Batas |
| --- | --- | --- |
| Data Integration | Menemukan aset dan bukti Maximo, PI, local DCS Historian beserta asal dan kualitasnya | Collector/kontrak existing; DCS masih rencana discovery, bukan integrasi yang sudah tersedia |
| PdM Center | Mencatat inspeksi manual, membaca riwayat, menyimpan analisis manusia dan review | Rekam sumber provisional tidak otomatis menjadi pengukuran kanonis atau evidence Case |
| Reliability Performance | Menelusuri riwayat aset dan, setelah kontrak disahkan, failure events/MTBF/MTTR | Aktivitas maintenance bukan failure; KPI yang belum memenuhi kontrak tidak diberi angka |

Tetap Next.js + FastAPI, collector dan owning store existing. Tidak ada migrasi framework, database baru, penghapusan modul, diagnosis otomatis, threshold baru atau write Maximo. CEMS dan NK tetap komponen existing; bukan perluasan lingkup PdM ini.

## Layar minimum dan pekerjaan harian

Lima pintu navigasi: **Beranda, Aset, PdM Center, Tindak Lanjut, Laporan**. Integrasi, kualitas data dan panduan tetap dapat ditemukan lewat utilitas berizin; bukan modul yang dihapus.

Untuk pekerjaan PdM biasa engineer hanya memerlukan **Register → Editor → Detail**, dengan riwayat sebagai tampilan kontekstual dari aset/inspeksi yang sama. Case dan Recommendation adalah cabang tindak lanjut, bukan prasyarat memasukkan pengukuran.

1. Dari PdM Center pilih **Input Pengukuran**. Pilih asal pekerjaan dan aset berotorisasi. Asal boleh belum diketahui; tidak ada default yang mengarang asal lama.
2. Masukkan nilai manual atau gunakan jalur sumber workbook yang sudah tersedia. Pembacaan arsip dan pengetikan provisional bukan tombol unggah/import massal baru.
3. Baca riwayat aset/titik yang relevan; bedakan **inspeksi**, **pengukuran asli**, **riwayat sumber Excel**, dan **audit revisi**. Jumlahnya tidak boleh dijumlahkan menjadi satu angka “data”.
4. Catat observasi, hipotesis dan analisis engineer secara terpisah. Saran naratif tidak otomatis menjadi Recommendation.
5. **Simpan draf**, baca kembali, lalu **Ajukan inspeksi**. Reviewer independen menerima, mengembalikan atau menolak rekam; approval bukan pernyataan aset sehat atau izin kerja.
6. Bila investigasi formal dibutuhkan dan evidence memenuhi syarat, buka Engineering Case dari detail. Rekam provisional tetap ditolak sebagai evidence Case, termasuk setelah approval.
7. Buat/review Recommendation melalui layanan existing. Catat SR yang dilaporkan atau tautkan WO existing sesuai mekanisme yang sudah ada. NADI tidak membuat SR/WO dan tidak mengubah statusnya di Maximo.

Alur rinci dan kondisi gagal: [User journey](NADI-PDM-USER-JOURNEY.md). Penempatan semua modul: [Navigation](NADI-UX-NAVIGATION-SIMPLIFICATION.md). Tidak perlu mengerti nama kontrak atau controller untuk menyelesaikan alur ini.

## Informasi minimum

| Layar | Terlihat langsung | Dibuka bila perlu | Tindakan utama |
| --- | --- | --- | --- |
| Inspection Register | Aset/label yang boleh dilihat, metode, waktu dan ketelitiannya, ringkasan observasi, status review, revisi, jumlah inspeksi sesuai filter dan posisi halaman | ID lengkap, clock sumber, asal pekerjaan, provenance dan detail batas filter | Input Pengukuran; Buka inspeksi adalah tindakan baris |
| Measurement Editor | Asal pekerjaan (termasuk unknown), aset, metode/versi, mode input, titik/parameter/nilai bertipe/unit/waktu asli, observasi; ringkasan analisis manual | Instrumen/prosedur/orientasi/konteks, source clocks, metadata evidence, SR yang dilaporkan; semua field existing tetap tersedia | Simpan draf; pengajuan dilakukan setelah readback pada detail |
| Inspection Detail | Aset, asal, metode/versi, waktu, nilai asli, observasi, analisis manual, status/revisi, langkah berikutnya yang diizinkan | Sel/hash/header/formula/cache, attachment metadata, alasan review, audit/revisi, SR/WO dan Case terkait | Ditentukan state/role: Ubah, Ajukan, Mulai review, atau keputusan review |

Progressive disclosure mengubah penempatan, bukan payload atau validasi. Nol tetap nol, null tetap tidak diketahui. Date-only tidak menjadi midnight; waktu input bukan waktu pengukuran. Jika kelompok akuisisi berbeda, jangan menggabungkannya ke satu inspeksi demi menyederhanakan layar.

## Kondisi riil yang menjelaskan kebingungan

Main yang diverifikasi adalah `f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. PR107 **OPEN**, bukan merged. Read-only runtime checks menemukan source aktif berbeda dari main; identitas rinci hanya disimpan dalam audit privat PO. [Audit publik](NADI-PDM-REPOSITORY-AUDIT.md) menjelaskan batas pembuktiannya.

Register inspeksi dan arsip kelompok sumber Excel adalah dua populasi berbeda. Register satu-inspeksi-per-halaman dan jalur Excel di dalam Riwayat & Tren membuat data yang telah diimpor mudah terlewat. Mengubah jumlah baris/byte limit bukan solusi Sprint1. Cakupan manifest historis yang sudah terdokumentasi bukan hitungan inspeksi atau sertifikat visibility per pengguna saat ini.

## Riwayat Excel: tersedia, provisional, dan tetap berizin

[Complete-history](nadi-pdm-complete-history-01.md) mempertahankan 7 workbook/200 sheet, literal scalar, formula/cache tanpa eksekusi, coordinate/hash/profile, source clocks, RAW/context dan alias immutable. [Proposal lama](nadi-complete-demo-activation-proposal.md) adalah checkpoint sebelum aktivasi; kata “UNEXECUTED” di sana tidak boleh dipakai sebagai status runtime hari ini. Tabel dan data history sekarang sudah ada; tugas ini tidak menjalankan migrasi007 atau import ulang.

| Keputusan berikutnya | Gate yang harus ditutup | Otoritas |
| --- | --- | --- |
| Membaca arsip existing | Login normal, AUTHOR owner/asset scope per occurrence, hak akses source, baca batch/alias tanpa bocor scope | Layanan existing; tidak perlu grant massal baru |
| Mengaktifkan kandidat source berikutnya | Baseline FE/BE/controller/ledger/serializer terverifikasi; kompatibilitas runtime aktif dengan main, review/CI exact SHA, backup/recovery segar, persetujuan paired cutover dan UAT | Operator + reviewer + PO; **di luar tugas ini** |
| Import baru/resume | Bukti hak custodian X02, target/manifest/source/parser/alias/approval/preflight terikat, batas chunk/receipt dan backup13-table segar ≤15 menit; rekonsiliasi perubahan manusia; selective recovery direview | Custodian + operator + PO, izin per aksi; jangan replay import lama hanya karena UI kosong |
| Menjadi pengukuran/evidence kanonis | G01/G02, V01–V05, T01–T04, MC01–MC04, TH01–TH05 pada matriks engineer; Q01–Q10; typed frozen evidence projection dan bound teruji | Engineer disiplin + owner aset; semua keputusan pending sampai bukti keputusan ada |
| Tren lintas inspeksi/portable–PI/DCS | V06/T05/MC05/TH06 serta X01/X02, acquisition/point/unit/time/comparability/custody disahkan | Engineer + owner data; tidak mengikuti approval rekam secara otomatis |

Daftar keputusan dan bukti persis tetap di [validation matrix](nadi-pdm-eng-validation-01.md) dan [input contract](nadi-pdm-input-first-contract-01.md). SOURCE_READY berarti terbaca, bukan sah secara engineering. Runtime juga memiliki overlay interpretasi/estimasi terpisah yang belum ada di main; pertahankan raw, disclosure dan batas nonkanonisnya. Sprint 1 tidak menambah estimasi, tidak memasukkannya ke grafik kanonis, Case atau KPI.

## Persetujuan yang diminta dari PO

Setujui lima pintu navigasi, tiga layar inti dan cabang Case yang bersyarat. Setujui hanya [Sprint 1](NADI-PDM-ROADMAP-AND-SPRINT-1.md): memperjelas entry point dan istilah dengan perilaku existing tetap utuh. Setiap fitur harus lolos [preservation matrix](NADI-PDM-FEATURE-PRESERVATION.md). Discovery sumber, KPI, import/activation dan rollout tetap membutuhkan keputusan terpisah. Tidak ada phase yang otomatis dinyatakan selesai oleh blueprint ini.

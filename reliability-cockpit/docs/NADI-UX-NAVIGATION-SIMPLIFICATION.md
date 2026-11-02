# Penyederhanaan navigasi NADI

Usulan penempatan, bukan penggantian URL/API atau penghapusan modul. [Audit route lengkap](NADI-PDM-REPOSITORY-AUDIT.md) membatasi inventaris pada source main yang dipin.

| Navigasi utama | Entry existing | Isi/konteks yang dipertahankan | Satu aksi utama |
| --- | --- | --- | --- |
| Beranda | `/` | Ringkasan faktual dan perhatian yang bisa ditelusuri; status data beralasan | Buka pekerjaan/aset yang dipilih; tidak membuat health score |
| Aset | `/assets` | Detail asset; overview/timeline/maintenance/FMEA/health/overhaul; assessment register `/asset-health` | Buka aset |
| PdM Center | `/pdm` | Register, editor, detail, pengukuran asli, riwayat sumber Excel, audit | Input Pengukuran pada register AUTHOR; aksi lain mengikuti state |
| Tindak Lanjut | `/action-board` | Recommendation `/recommendations`; Case `/engineering/cases`; review, advisory/inbox secara kontekstual | Buka item untuk ditindaklanjuti/review sesuai role |
| Laporan | `/reports` | Coverage, maintenance dan bukti existing; KPI hanya setelah kontrak disahkan | Pilih/buka laporan |

Utilitas berizin: Integrasi (`/system-integration`), kualitas/provenance (`/data-quality`), panduan (`/panduan/istilah`), akun/tema/logout. Administration tetap planned, bukan fitur admin baru. Pada mobile utilitas tetap dapat ditemukan melalui menu berlabel, bukan tautan tersembunyi tanpa nama.

## Jalur kontekstual seluruh fitur

- Aset → maintenance `/maintenance`, investigasi `/maintenance/investigation`, WO `/work-orders`, FMEA `/fmea`, overhaul `/overhauls`. `/equipment/[id]` tetap technical compatibility path; bukan daftar asset bisnis kedua.
- RCFA `/rcfa` tetap register global dari konteks laporan/integrasi. Hubungan asset RCFA belum terverifikasi; **jangan** membuat tautan per-asset palsu.
- Detail inspeksi → audit `/engineering/local?resource=inspections&record=…`; Case eligible → `/engineering/cases?record=…`; Recommendation → detail/review/follow-up existing. Seluruh deep link dan parameter record dipertahankan.
- `/engineering`, `/engineering/[caseId]`, `/engineering/workflow`, `/engineering/qa`, `/engineering/local`, `/engineering/lab` tetap entry existing dengan batas QA/role dan data masing-masing. Entry lab/QA bukan menu pekerjaan harian dan tidak dijadikan jalur produksi baru.
- Advisory `/engineering/advisories` dan Inbox `/engineering/inbox` tetap dapat ditemukan dari item tindak lanjut yang relevan oleh pengguna berizin; ACK bukan bukti pelaksanaan pekerjaan.
- `/login` tetap standalone; session authority, asset scope dan pesan denied tidak diubah.

## Duplikasi dan transisi yang membingungkan

| Bukti existing | Usulan terbatas | Yang tidak boleh hilang |
| --- | --- | --- |
| Sidebar Recommendation dan Action Board terpisah; Engineering workspace terpisah lagi | Satu entry Tindak Lanjut dengan subview/link bernama jelas | Register, detail, review, history dan akses direct URL |
| `/pdm` menampilkan QA boundary, fakta method PENDING/condition NOT ASSESSED, help filter, lalu penjelasan provisional lagi pada detail/history | Satu pemberitahuan QA ringkas yang tetap terlihat; panel “Batas penggunaan”; alasan blocking selalu di tempat aksi | PENDING/NOT ASSESSED tidak diubah menjadi valid/healthy; warning estimasi runtime tetap terlihat saat estimasi ditampilkan |
| Riwayat & Tren memuat source history dan canonical history dengan konsep berbeda | Nama subbagian “Pengukuran asli” dan “Sumber Excel”; jumlah dan filter masing-masing | Endpoint, keyset/byte pagination, current authorization dan larangan canonical plot untuk capture |
| Tabel register mengisi observasi panjang, raw IDs dan seluruh konteks | Ringkasan tanpa menghapus detail; ID/provenance di detail/expand | Tidak mengubah limit=1/budget existing atau mengklaim semua35 rekam tampil |
| Detail → workflow audit di `/engineering/local`; Cancel editor bisa kembali ke detail sebelumnya | Label eksplisit “Riwayat revisi”, “Kembali ke daftar”, “Batal perubahan”; kembalikan konteks asset/filter | Unsaved guard, fokus keyboard, sesi dan immutable revision |
| Analisis Engineering global selalu tampak seperti langkah wajib | Aksi Case dari record yang eligible, dengan jalur Case existing tetap discoverable | Native frozen evidence/revision validation dan server rejection untuk provisional |

## Aturan form dan aksesibilitas

Primary button mengikuti state, bukan selalu Save/Create. Grup pilihan keputusan review dapat memiliki satu primary yang dipilih secara sadar; tidak default APPROVED. Secondary actions tetap berlabel dan keyboard accessible. Panel yang dilipat tidak boleh menyembunyikan error, reason yang wajib atau field wajib yang belum valid; buka panel dan pindahkan fokus saat validasi. Tidak menghapus payload, auto-fill unit/metode, menggabungkan clock atau menghilangkan audit demi keringkasan.

Sprint1 tidak membuat route baru, menambah wizard multi-step, memperbesar page size, mengganti status/DTO atau mendesain dashboard baru. Navigasi kembali, responsive drawer, dark mode, login, direct deep links dan draft persistence existing wajib diuji.

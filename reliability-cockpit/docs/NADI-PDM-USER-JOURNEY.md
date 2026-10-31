# NADI PdM — satu perjalanan engineer

Usulan UX; backend, role dan state machine existing tetap authoritative. Mulai dari [blueprint](NADI-PDM-PRODUCT-BLUEPRINT.md).

| Langkah | Engineer melihat/melakukan | Data/state existing | Hasil dan jalan keluar |
| --- | --- | --- | --- |
| 1. Pilih pekerjaan | Input Pengukuran → Permintaan bidang / Temuan PdM PM52 / Belum dicatat; pilih aset sesi | `work_origin` optional; department wajib hanya untuk DEPARTMENT_REQUEST; canonical asset bukan label sumber | Unknown tetap unknown; aset tak berizin ditolak server. Pemilihan PM52 menghapus department lama, bukan menyembunyikannya |
| 2. Masukkan nilai | Pilih native atau workbook provisional; isikan sumber/titik/nilai/unit/waktu pada ketelitian aslinya | Native1.0/1.1, capture1.2, origin1.3, notes/SR1.4; native measurements tidak bercampur dengan capture | Nilai kosong bukan0; unit tidak ditebak; formula tidak dieksekusi; acquisition berbeda tetap terpisah |
| 3. Periksa riwayat | Buka Riwayat dengan konteks aset/titik; pilih Pengukuran asli atau Sumber Excel secara eksplisit | Native measurement-history berbeda dari source-history; revisi lama melalui audit immutable | Ringkasan menunjukkan jenis/populasi/halaman. Tidak ada join otomatis data portable dengan historian |
| 4. Analisis manusia | Tulis observasi, hipotesis, catatan analisis dan saran tindak lanjut yang dapat dibedakan | `engineering_analysis` HUMAN_ENTERED_ENGINEER_NOTES; follow-up notes mensyaratkan analysis notes | Tidak mengubah SOURCE_ASSESSMENT menjadi diagnosis aplikasi; tidak otomatis membuat entity Recommendation |
| 5. Simpan dan ajukan | Simpan draf → readback exact record/revision → Ajukan inspeksi | Receipt/request intent existing; CAS expected_revision; DRAFT→SUBMITTED | Belum tersimpan tidak diberi success. Lost ACK memakai intent sama; konflik memperlihatkan revisi terbaru, tanpa overwrite diam-diam |
| 6. Review independen | Reviewer melihat nilai asli dan rationale; mulai review lalu pilih keputusan | SUBMITTED→UNDER_REVIEW (legacy IN_REVIEW dibaca)→APPROVED/RETURNED/REJECTED | Author/inspector/contributor tidak boleh self-review. RETURNED/REJECTED kembali lewat revise existing, bukan mengedit rekam terkunci |
| 7. Investigasi bila perlu | Setelah readback/review, putuskan apakah analisis naratif cukup atau perlu Case | Hanya inspeksi native APPROVED eligible untuk frozen exact-revision Case handoff | Capture: alasan PROVISIONAL_INPUT_NOT_CASE_EVIDENCE, tanpa tombol palsu. Case created tetapi link gagal tetap ditunjukkan sebagai dua hasil terpisah; retry link tidak menggandakan Case |
| 8. Recommendation dan tindak lanjut | Dari Case/asset evidence gunakan create/review Recommendation existing; catat reported SR atau referensi WO existing | Review Recommendation independen; local follow-up PROPOSED→PLANNED→IN_PROGRESS→COMPLETED, atau CANCELLED sesuai layanan | SR REPORTED_UNVERIFIED bukan WO; tidak lookup/create/close SR/WO di Maximo. Approval rekam bukan izin eksekusi pekerjaan |

## Skenario praktis tanpa mengarang data

Engineer menerima permintaan bidang untuk aset yang memang tersedia di scope. Ia membuka editor, memilih asal/asset dan menyalin pembacaan asli dengan unit/waktu yang benar-benar diketahui. Riwayat dapat memperlihatkan workbook yang belum terikat ke asset operasional: ia membacanya sebagai bukti sumber, bukan mengesahkan mapping. Analisis ditulis manusia; bila belum ada kesimpulan, NOT ASSESSED tetap jujur. Setelah simpan dan review independen, pekerjaan dapat berakhir sebagai rekam yang dapat ditelusuri. Case hanya dibuat jika ada pertanyaan investigasi yang perlu dikelola dan evidence memenuhi gate.

Tidak semua inspeksi memerlukan Case, Recommendation atau SR. Tidak semua data historis merupakan measurement kanonis. Case manual existing tetap dapat diakses oleh role berizin; menyembunyikan menu tingkat atas tidak menghapus kemampuan tersebut.

## Gangguan dan keamanan alur

- Navigasi yang membuang input meminta konfirmasi; Cancel mengembalikan konteks sebelumnya. “Kembali ke daftar” harus jelas berbeda dari “Tutup detail”.
- Draft in-memory hanya dipulihkan pada identitas/scope yang sama. Logout, revocation atau perubahan subject/role/scope membersihkan data privat; tidak menjanjikan draft tahan browser restart.
- 401/403/503, data kosong dan backend tidak kompatibel tetap kondisi berbeda. Ringkasan halaman tidak memakai data mock, fallback aset atau angka0 untuk kegagalan baca.
- Jika hak melihat arsip sumber berbeda dari hak melihat inspeksi, pertahankan gate per occurrence; jangan menawarkan “tampilkan semua workbook” sebagai perbaikan UX.
- Alur review Case, Recommendation, Advisory dan Inbox/ACK tetap independen dan diaudit; perpindahan konteks tidak menandakan seluruh rantai selesai.

## Minimum acceptance untuk PO

Dengan fixture synthetic berizin yang sudah ada, engineer dapat menyelesaikan 1–6 tanpa membuka panel teknis atau Case wajib. Reviewer yang berbeda dapat mengembalikan satu draf untuk koreksi. PO dapat menjelaskan kapan tahap7 dilarang, membedakan SR/WO, serta menemukan kembali nilai asli, revisi dan alasan keputusan. Ini rencana UAT masa depan, bukan hasil UAT tugas dokumentasi ini.

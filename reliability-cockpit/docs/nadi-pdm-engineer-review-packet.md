# Lembar keputusan engineer — kesiapan M02

Revisi Sprint 2 · 1 November 2026. Paket diskusi ringkas, **bukan sign-off**.
Seluruh keputusan di bawah tetap PENDING_ENGINEER_VALIDATION. Rincian pertanyaan,
alias K1–K9 dan koordinat sumber ada pada [matriks authoritative](nadi-pdm-eng-validation-01.md).
Tidak ada nilai plant, identitas privat atau jawaban engineer yang direka.

## Satu sesi yang dapat diselesaikan

1. Owner aset dan engineer berwenang memilih **satu keluarga Vibration V/H/A**
   representatif K4–K7. Custodian menunjukkan bukti yang boleh dilihat; tidak perlu
   membuka200 sheet. Catat perbedaan/pengecualian titik yang benar-benar ada.
2. Putuskan G01/G02 dahulu, lalu V01–V05. Cocokkan sketsa titik dengan prosedur,
   besaran/unit, acquisition, instrumen dan waktu. Label 1V/1H/1A bukan binding fisik.
3. Catat jawaban per ID dengan owner bukti, scope, metode/versi, keputusan dan tanggal.
   Pilihan ACCEPTED/REJECTED/DEFERRED hanya diisi setelah keputusan berwenang;
   bidang kosong atau Codex fixture tidak dianggap persetujuan.
4. Lanjutkan Tribology, MCSA dan IRT/CEP saat owner/evidence tersedia. P2 boleh
   ditunda; penundaan tidak membuka tren atau assessment. Simpan revisi keputusan
   terdahulu beserta alasan pengganti, lalu tautkan ke matriks rinci.

| Identitas sesi | Isian engineer / owner |
| --- | --- |
| Engineer, disiplin dan kewenangan terkonfirmasi | — |
| Owner aset / custodian bukti | — |
| Keluarga K / lingkup titik dan pengecualian | — |
| Prosedur/metode versi yang ditelaah | — |
| Tanggal diskusi / rujukan bukti privat yang diizinkan | — |

## Register keputusan P1 — masing-masing tetap terpisah

Isi `bukti / owner`, `scope`, `metode / versi`, `keputusan / status`, `tanggal`
dan `pertanyaan tersisa` per baris. Jangan menyalin data sensitif ke GitHub.

| ID | Keputusan yang diperlukan | Bukti / owner | Scope | Metode / versi | Keputusan / status | Tanggal | Pertanyaan tersisa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | Binding aset exact dan lokasi sumber | — | — | — | PENDING_ENGINEER_VALIDATION | — | Bukti binding mana? |
| G02 | Otoritas, prosedur dan batas persetujuan | — | — | — | PENDING_ENGINEER_VALIDATION | — | Siapa berwenang untuk scope ini? |
| V01 | Lokasi fisik, nomor dan V/H/A yang benar-benar ada | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | Sketsa/rujukan titik? |
| V02 | Quantity, unit dan RMS/p-p | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | mm/s dan mm/s-rms setara di scope ini? |
| V03 | Portable/installed/UNKNOWN, acquisition dan bandwidth | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | Bukti pengambilan mana? |
| V04 | Instrumen, mounting, kalibrasi dan prosedur | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | Berlaku untuk titik yang mana? |
| V05 | Waktu ukur asli, zona/precision dan operasi | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | Ukur, rekap atau tanggal laporan? |
| T01 | Titik sampling, equipment dan sampel | — | — | Tribology / — | PENDING_ENGINEER_VALIDATION | — | FAN/MILL scope sama atau berbeda? |
| T02 | Besaran/unit lab, original vs derived | — | — | Tribology / — | PENDING_ENGINEER_VALIDATION | — | % tidak diasumsikan ppm |
| T03 | Lab, instrumen dan metode authoritative | — | — | Tribology / — | PENDING_ENGINEER_VALIDATION | — | Rujukan laporan/prosedur? |
| T04 | Waktu sampling, analisis dan laporan | — | — | Tribology / — | PENDING_ENGINEER_VALIDATION | — | Mana measured-at yang sah? |
| MC01 | Equipment, fase dan lokasi listrik | — | — | MCSA / — | PENDING_ENGINEER_VALIDATION | — | Binding exact mana? |
| MC02 | Besaran/unit dan input vs hitung/assessment | — | — | MCSA / — | PENDING_ENGINEER_VALIDATION | — | RMS tidak menebak A/V |
| MC03 | Acquisition, instrumen, prosedur dan beban | — | — | MCSA / — | PENDING_ENGINEER_VALIDATION | — | Konteks operasi yang diperlukan? |
| MC04 | Timestamp capture dan zona/precision | — | — | MCSA / — | PENDING_ENGINEER_VALIDATION | — | Tanggal/jam sumber mana? |
| TH01 | Tiga unit temperatur bearing yang ambigu | — | — | Thermal/CEP / — | PENDING_ENGINEER_VALIDATION | — | Bukti unit masing-masing? |
| TH02 | Routine thermal vs IRT dan arti IR Window | — | — | IRT/CEP / — | PENDING_ENGINEER_VALIDATION | — | Profil ini benar IRT atau OTHER? |
| TH03 | Kamera, thermogram, aset/titik/waktu | — | — | IRT / — | PENDING_ENGINEER_VALIDATION | — | Custody belum dibuktikan metadata |
| TH04 | Reference/ambient, emissivity dan prosedur | — | — | IRT/CEP / — | PENDING_ENGINEER_VALIDATION | — | Apa yang diwajibkan prosedur? |
| TH05 | Input asli, Delta T/formula dan assessment | — | — | IRT/CEP / — | PENDING_ENGINEER_VALIDATION | — | Kalkulasi/limit membutuhkan keputusan terpisah |

## Register P2 — tidak aktif otomatis

| ID | Keputusan lanjutan | Bukti / owner | Scope | Metode / versi | Keputusan / status | Tanggal | Pertanyaan tersisa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V06 | Kesetaraan titik/unit/bandwidth/mounting/operasi | — | — | Vibration / — | PENDING_ENGINEER_VALIDATION | — | Kapan dua inspeksi boleh dibandingkan? |
| T05 | Titik sampling, pelumas dan lab/metode | — | — | Tribology / — | PENDING_ENGINEER_VALIDATION | — | Kapan hasil harus dipisahkan? |
| MC05 | Fase/lokasi, beban, instrumen/acquisition | — | — | MCSA / — | PENDING_ENGINEER_VALIDATION | — | Kriteria comparability? |
| TH06 | Reference/Delta T, comparability dan otoritas | — | — | Thermal/IRT / — | PENDING_ENGINEER_VALIDATION | — | Tidak mengaktifkan threshold/grade |
| X01 | Cadence dan pemicu pengambilan | — | — | Per metode / — | PENDING_ENGINEER_VALIDATION | — | Gap tidak diisi sebagai jadwal harian |
| X02 | Custody dan izin pemakaian historis | — | — | Per sumber / — | PENDING_ENGINEER_VALIDATION | — | Izin import/custody tetap terpisah |

**Q01–Q10 tetap PENDING.** Review rekam inspeksi ≠ validasi metode ≠ penilaian
kondisi equipment ≠ izin maintenance. Field `method_version`, APPROVED, grafik
fixture, label DIRECT atau screenshot bukan keputusan engineer.

[Contoh Vibration SINTETIS](evidence/nadi-pdm-workbook-02/boiler-three-point-rms-light-1440.png) ·
[Tribology SINTETIS](evidence/nadi-pdm-workbook-01/area_fan-1440.png) ·
[MCSA SINTETIS](evidence/nadi-pdm-workbook-01/logsheet_6kv-1440.png) ·
[CEP SINTETIS](evidence/nadi-pdm-workbook-02/cep-bearing-cbm-light-1440.png).

Jawaban berwenang berikutnya harus dikaji sebagai kontrak M02 dan comparability
berversi sebelum implementasi lanjutan. Paket ini tidak menambah metadata bebas,
registry titik, DTO, canonical mapping, source request, import atau approval runtime.

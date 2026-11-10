# Operasi: draft BOIL dan detail baca-saja

Menu Operasi (`/operations`) mempertahankan susunan visual dari foto referensi
pengguna: Mill G–A di kiri, drum/furnace dan economizer di tengah, fan serta
feedwater/fuel oil di kanan. Ini draft display-only, bukan diagram engineering/
P&ID tervalidasi, pengganti HMI, alarm, atau kontrol DCS.

## Hasil audit dan perubahan 9 November 2026

- Sebelumnya 18 simbol hanya nonaktif, sehingga label tidak bisa ditelusuri.
  Sekarang klik simbol membuka **detail draft**, bukan detail Asset hasil tebakan.
- Hasil filter/pagination Registry sebelumnya kembali tersembunyi di disclosure.
  Panel kini tetap terbuka ketika query Registry dikirim, termasuk filter kosong,
  unit `0`, dan offset nol. Layar/detail terpilih dipertahankan pada form dan pager.
- Tujuh tombol layar sebelumnya disabled. TURB, ECS, DEH, CCS, FSSS, CHM, MEH
  kini dapat dibuka, tetapi hanya menunjukkan **Referensi belum tersedia** dan
  kebutuhan verifikasi. Tidak ada equipment, diagram, parameter, kepanjangan
  singkatan, atau proses tambahan yang dikarang.
- README menyatakan Supervisor tidak punya approval, bertentangan dengan Gate
  dan fitur Reliability yang sudah ada. Penjelasan role diselaraskan ke approval
  exact snapshot Asset/tahun; tidak ada perubahan izin atau fungsi approval.

## Batas data dan interaksi

- Nilai parameter selalu `—`, bukan angka foto atau data live. Timestamp kosong,
  kualitas `unknown`. Tidak ada binding, polling, atau kontrol sumber baru.
- Nama equipment adalah label visual referensi, bukan canonical Asset ID atau
  tag terverifikasi. `OperationsDraft` hanya katalog lokal 18 simbol yang sudah
  ada, dengan label kelompok dan satuan dari draft yang sama.
- Detail memakai **Indikator 1, 2, ...** karena arti parameter dan tag belum
  diverifikasi. Satuan tetap berlabel perlu verifikasi, tanpa konversi/normalisasi.
- `screen` dan `component` memakai allowlist server sebelum pembacaan Mart.
  Component BOIL pada layar lain ditolak. Tidak ada dynamic include dari input.
- Tautan simbol mengarah ke GET `/operations?screen=BOIL&component=…` dengan
  anchor panel. Daftar komponen HTML menjadi alternatif keyboard/assistive
  technology untuk diagram SVG. Tombol **Tutup detail**, Back/Forward, bookmark,
  dan navigasi layar tidak membutuhkan JavaScript atau endpoint mutasi.
- Default Asset Wellness **belum dinilai**, dengan simbol abu-abu. Checkbox
  **Contoh warna wellness** hanya mengubah warna lokal melalui CSS. Banner
  **SIMULASI WARNA · bukan kondisi aset** muncul saat aktif. Detail tetap belum
  dinilai, terpisah dari contoh warna. Garis putus-putus menandai simbol terpilih,
  bukan alarm atau tingkat wellness.
- Status operasi **Unknown**, alarm DCS **Tidak terhubung**, dan Asset Wellness
  dipisahkan pada detail maupun placeholder. Tidak terhubung bukan bebas alarm.
  Warna jalur membedakan media proses, bukan kondisi aset.
- Konteks Registry existing dipertahankan terpisah. Filter, pagination, identitas
  exact, pembatasan BSR/IP, dan Gate inspeksi tetap berlaku. Memilih Asset tidak
  otomatis memetakan simbol. Pemetaan Asset/tag pada detail tetap kosong.
- Diagram scroll horizontal terbatas pada layar kecil. Detail/status/pemetaan
  menjadi satu kolom pada mobile. Tidak ada perubahan schema, SQLite operational,
  collector, historian, PLC, autentikasi, atau koneksi sumber.

## Implementasi

- `app/Services/OperationsDraft.php`: katalog label draft, bukan registry sumber.
- `app/Http/Controllers/OperationsController.php`: validasi pilihan lokal.
- `resources/views/operations/index.blade.php`: navigasi layar/disclosure Registry.
- `resources/views/operations/boiler-draft.blade.php`: SVG existing dan link lokal.
- `resources/views/operations/component-detail.blade.php`: detail placeholder.
- `resources/views/operations/screen-placeholder.blade.php`: layar tanpa referensi.
- `resources/css/operations-draft.css`: layout, fokus, penanda pilihan dan mobile.
- `tests/Feature/OperationsTest.php`, `tests/Frontend/operations.test.js`: regresi.

## Publication verification

See [public-source integration](publication.md) for the checks run against this
publication branch. Historical feature QA is not a fresh browser pass or an
engineering signoff. No source records, private catalogs, runtime data, database
activation, merge or deployment are included in publication.

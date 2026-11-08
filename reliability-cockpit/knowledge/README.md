# Knowledge integration untuk NADI

BSLA adalah **satu monorepo**, bukan kumpulan repository yang perlu di-clone atau
ditambahkan sebagai submodule. Backend FastAPI di `reliability-cockpit/` dan
[NADI Laravel](../../NADI/README.md) memakai kontrak serta pengetahuan bersama:

```text
BSLA/
├── maximo-knowledge/           # object/field/scope evidence
├── pi-knowledge/               # verified technical registry and mappings
├── reliability-data-contracts/ # semantic contracts
├── maximo-collector/           # source store + local Mart projection
├── reliability-cockpit/        # query API + retained legacy UI
└── NADI/                       # active Laravel consumer
```

Gunakan sibling path/mount existing sesuai konfigurasi komponen. Tidak perlu
membuat nested Git, DB, symbolic link absolut baru, worktree atau handoff rutin.
Sumber identifier harus terverifikasi; technical tag tidak otomatis governed
Asset signal. Consumer tidak melakukan discovery ulang atau menerima credentials
produksi. Field vendor tetap dalam adapter/`sources.*`; public DTO lebih sempit.

Baca [root workflow](../../AGENTS.md), [backend rules](../AGENTS.md),
[contracts](../../reliability-data-contracts/README.md), serta
[roadmap MTBF/MTTR](../../plans/MTBF-MTTR.md). Bukti teknis yang ada belum menjadi
persetujuan definisi failure, exposure atau repair interval.

# Safe PI Discovery Scripts

Ikuti [AGENTS PI](../AGENTS.md) dan [workflow solo developer](../../AGENTS.md).
[NADI Laravel](../../NADI/README.md) tidak menjalankan script ini saat dibuka.
Gunakan evidence/fixtures lokal untuk pengembangan rutin. Source discovery tetap
opt-in; authentication tidak boleh dicoba ulang otomatis sebagai efek samping task ini.
Histori exposure untuk [MTBF/MTTR](../../plans/MTBF-MTTR.md) belum tersedia hanya
karena registry/script ada; tidak menebak tag atau membuat collector paralel.

All discovery scripts must:

- perform read-only requests only
- use conservative request rates
- have explicit timeouts
- load secrets from environment variables
- redact Authorization/session output
- avoid bulk historical downloads by default
- store metadata first, data samples second

# PI Knowledge

## Konteks workspace dan rencana reliability

Knowledge ini mendukung PI Collector existing dan rencana historian
[NADI Laravel](../NADI/README.md), belum operating-exposure integration aktif.
Lihat [roadmap MTBF/MTTR](../plans/MTBF-MTTR.md). Technical attribute registry
bukan governed Asset signal; mapping, state/quality, clock alignment dan coverage
harus tervalidasi sebelum interval dipakai sebagai operating hours.

Ikuti [AGENTS](AGENTS.md) dan root: solo developer langsung checkout aktif,
edit → uji lokal → lihat hasil. Jangan retry authentication, discovery atau
backfill sebagai efek samping merapikan UI; verifikasi runtime dan izin terlebih dahulu.
Read stored data tidak membuktikan source freshness.

Read-only knowledge base for the central PI Web API / PI Asset Framework
operational boundary used by NADI discovery.

The existing acquisition path remains outside this repository:

```text
DCS / control systems → existing OPC / PI Interface pipeline
    → central PI Data Archive / PI AF → PI Web API → future NADI evidence
```

PI Vision is a visualization surface. It is not treated as a second source
system. PI Web API is the supported integration candidate only where an
instance-verified GET contract exists.

This repository records:

- Data Servers
- PI Points / Tags
- Asset Servers
- AF Databases
- Elements
- Attributes
- WebIds
- units of measure
- stream access patterns
- recorded/interpolated/summary capabilities
- unit-specific equipment mappings

The existing `../pi-collector/` owns collection. This knowledge component does not
create another collector; verified AF/stream evidence and runtime-only credentials
remain required. The NADI exposure/orchestration consumer is future work.

## Principle

A PI tag alone is not enough.

The target is semantic knowledge such as:

```text
BFP 1A Motor DE Bearing Temperature
→ equipment: BFP-1A
→ parameter: bearing_temperature
→ position: motor_drive_end
→ unit: degC
→ source: PI
→ tag/webid: verified source identifier
```

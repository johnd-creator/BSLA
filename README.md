# BSLA

Starter workspace for building a reusable organizational data knowledge layer around:

- IBM Maximo APIs
- AVEVA/OSIsoft PI Web API / PI Vision-adjacent data access
- Reliability semantic contracts
- Application consumers such as Reliability Cockpit

## Repository Layout

```text
BSLA/
├── maximo-knowledge/
├── pi-knowledge/
├── reliability-data-contracts/
├── reliability-cockpit/
├── pi-collector/
├── maximo-collector/
├── cems-collector/
├── NK/
└── NADI/                 # Laravel development workspace
```

## NADI Laravel development

The new [NADI workspace](NADI/README.md) runs locally at
<http://127.0.0.1:8010/login>. Work directly in `NADI/` as a single developer:
small changes, focused tests, refresh the local preview. It contains four local
roles/accounts, Master Asset, Action Board drafts, read-only WO detail, BSR/CS01
mapping proposals, and a simple inspection→recommendation draft form.

The existing NADI FastAPI/Next.js preview and managed collectors remain separate.
The Compose project/volumes are still `reliability-cockpit-platform`. The old
`/home/john-d/Music/reliability-knowledge-starter` path remains a compatibility
symlink to `/home/john-d/Music/BSLA`; do not remove it while services reference it.
No operational database or source identity is replaced.

## Design Principles

1. Source knowledge is separated from applications.
2. Discovery must be read-only.
3. Knowledge must be both human-readable and machine-readable.
4. Business meaning must be recorded alongside technical API details.
5. Credentials, tokens, cookies, passwords, and sensitive production data must never be committed.
6. Applications should depend on semantic contracts rather than vendor-specific APIs whenever possible.

This is a mono repository. Git is initialized at this root; the subprojects do
not contain nested Git repositories. Each project retains its own setup, test,
and run commands as documented in its `AGENTS.md` / `README.md`.

## Recommended Workflow

1. Start discovery inside `maximo-knowledge` and `pi-knowledge`.
2. Let Codex document verified endpoints and data structures.
3. Map technical source fields into reliability concepts.
4. Store shared entity definitions inside `reliability-data-contracts`.
5. Build application integrations from the knowledge repositories rather than rediscovering the source systems.

## Important

This starter contains templates only. Replace placeholders only after verifying them against your authorized environment.

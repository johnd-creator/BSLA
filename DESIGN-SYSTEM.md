# NADI Design System V1

Updated: 2026-10-10 · UX-02 implementation candidate — NADI UX Bundle A.
V1 tokens and compatible primitives are implemented; Product Owner visual acceptance remains pending.
Product Owner direction: professional industrial reliability platform, navy sidebar,
green active navigation, light content, white cards and clear information hierarchy.
The five existing root PNGs are [official, AVAILABLE references](docs/design/references/README.md)
confirmed by the Product Owner in FIX-02. Their visual mapping and original bytes
are verified; responsive comparison is recorded in the [Bundle A review](reliability-cockpit/docs/nadi-ux-bundle-a.md); final token/visual approval remains pending.

## Tokens

| Token | Proposed value | Intended use |
|---|---|---|
| sidebar-navy | `#102536` | Persistent navigation background |
| active-green | `#118C45` | Active navigation treatment |
| primary-green | `#16A34A` | Primary action/accent, subject to contrast check |
| warning-amber | `#F59E0B` | Explicit warning with text/icon |
| critical-red | `#DC2626` | Error/destructive interaction; governed severity only when approved |
| informational-blue | `#3B82F6` | Informational emphasis |
| background | `#F8FAFC` | Main canvas |
| surface | `#FFFFFF` | Cards and input surfaces |
| text-primary / secondary | `#0F172A` / `#475569` | Proposed neutral text |
| border / unknown | `#CBD5E1` / `#64748B` | Boundaries and explicitly unknown states |

Colors are design input, not engineering thresholds. Red/amber/green condition
states require approved engineering rules and sufficient evidence. Raw source
statuses remain neutral; Good signal quality does not mean healthy equipment.
Do not reuse illustrative screenshot values as production metrics.

Verify contrast for each text/background, selected/hover/disabled/focus and chart
combination before approval. White text on a green/amber/blue token is not assumed
readable. Use darker foregrounds or approved token adjustments after testing;
record the exact pair and measured ratio. Target at least 4.5:1 for ordinary text
and 3:1 for large text and meaningful controls, as a proposed product acceptance
target; this document does not certify accessibility conformance.

## Typography and spacing

Proposed system sans-serif stack; reuse existing licensed/system fonts until a
brand font is approved. Body 14–16px, line-height 1.5; page heading 28–32px/1.2;
section heading 20–24px/1.3; card heading 16–18px; label 12–14px; KPI value
28–36px. Use tabular numerals for values and explicit units/date bases. Avoid
all-cap paragraphs and long identifiers as primary labels; allow copy/inspection.

Spacing scale: 4, 8, 12, 16, 24, 32, 48px. Desktop page padding 24–32px,
mobile 16px; card padding 16–24px; grid gaps 16–24px. These are proposals rather
than exact font/interaction specifications inferred from flattened screenshots.

## Shell and navigation

Desktop sidebar proposed width 248px; optional collapsed state 72px with accessible
labels/tooltips. Topbar proposed minimum 64px, with page context, environment and
session controls. Development status must remain visible and must distinguish
factual data from synthetic Engineering fixtures. Avoid obscuring focus/anchors.

Use the [current/proposed navigation map](docs/design/NADI-UI-SPEC.md#navigation-map).
Highlight the actual current route; detail pages retain parent context and back
navigation. Submenus need keyboard activation and explicit expanded state. Preserve
direct URLs/bookmarks and all technical pages during any future relocation.
Do not introduce empty clickable modules as if they were operational.

## Components

| Component | Proposed standard |
|---|---|
| Cards | White surface, 1px neutral border, 12px radius; title, value/content, evidence/time context; no decorative score |
| Shadows | Subtle `0 2px 8px rgba(16,37,54,0.06)` for raised surfaces; border for ordinary grouping |
| Buttons | Primary/secondary/tertiary/destructive hierarchy; clear verb, visible focus, loading state, disabled reason; target 44px touch height |
| Forms | Persistent labels, unit/timezone/context beside fields, required/optional text; inline error plus summary; retain drafts on validation failure |
| Tables | Semantic headers, explicit units/date basis, scoped sort/filter/paging; textual status; horizontal overflow inside table, never whole page |
| Charts | Title, population, units, actual timestamps and evidence/as-of context; accessible summary/table; unknown intervals visible; no unsupported interpolation |
| Status badges | Text plus icon/tone; distinct UNKNOWN, NOT ASSESSED, DEMO and reviewed states; raw source values neutral |
| Dialogs | Labeled purpose, keyboard focus containment/return, explicit cancel; no ambiguous destructive confirmation |
| Evidence panels | Separate source fact, manual measurement, observation, interpretation, review and recommendation; version/time/quality remain inspectable |

Forms for Engineering mutations must reflect server authorization and revision
conflicts. A simulated reviewer in DEMO cannot authorize a real API action.
Existing primitives should be reused or deliberately evolved in a later task;
do not create a competing component library through this document.

## Interaction states

- Loading: stable skeleton/progress label; never display a temporary zero as a fact.
- Empty: distinguish no rows under current filters from unavailable evidence.
- Unknown: name the missing dependency; do not convert absence to healthy/normal.
- Error: keep shell and context, offer bounded retry, sanitize technical details.
- Stale: show age and approved policy basis separately from quality and condition.
- Success: identify the completed local action; do not imply a source WO changed.
- Conflict: explain that another revision exists, preserve authorized unsaved input
  and require deliberate reconciliation; no silent overwrite.
- Expired session: clear prior-user sensitive views, preserve security boundaries
  and lead to the existing authorized sign-in flow.

## Responsive and review requirements

Review 390px, 768px and 1440px widths plus zoom/long labels. On narrow screens,
sidebar becomes an accessible drawer, KPI grids stack, filters wrap and evidence
sections follow reading order. Dense tables may scroll in their own region with
visible affordance. Topbar controls remain reachable without obscuring content.
Preserve existing light/dark behavior until a separately reviewed transition;
the proposed light palette does not authorize removing the current theme.

Acceptance for a future implementation: all tokens/state pairs reviewed for contrast,
keyboard/focus and screen-reader labels checked, charts understandable without color,
no horizontal page overflow, screenshot comparison against actual approved originals,
factual routes unchanged, and PO visual decision recorded against the tested SHA.
Approval of this specification alone does not complete UX-02 or UX-09.

## Bundle A implementation decisions

The existing frontend now imports [V1 tokens](reliability-cockpit/web/app/design-tokens.css)
from its existing global stylesheet. Existing token names remain aliases so factual
and Engineering components share the same system. No runtime dependency was added.
Scoped ESLint/TypeScript/React hooks/accessibility tooling is development-only.

Implemented primary action green is **#0B7437**, replacing proposed #16A34A for
white-text actions. Automated luminance checks require ≥4.5:1 for normal text:
primary/white, light and dark text/surface, muted/surface, warning/surface and
sidebar text/navy. Navy remains #102536; green active navigation uses the darker
action shade with a visible green edge. Information badges do not classify health.

Spacing, radii, sidebar widths, topbar height, shadows and focus colors use tokens.
`ui.tsx` retains existing primitives and adds Button, InputControl, Breadcrumbs and
Feedback. TableFrame contains minimum width inside a keyboard-focusable labeled
scroll region. Loading/error states announce their purpose; raw statuses stay neutral.
The current dark theme is retained. This bounded review is not an accessibility
certification of all legacy Engineering forms.

Desktop navigation is 248px with an optional 72px collapse; below 1024px it is a
modal drawer with focus containment, Escape, focus return and background inertness.
The eight product entries follow the specified order. Unimplemented product modules
and PI/CEMS integrations are labeled Planned; no unrelated redirects are introduced.
Engineering remains a separate authorized link pending PO placement review.

Measured token pairs (WCAG relative luminance, rounded): white/#0B7437 **5.89:1**;
sidebar #E2E8F0/#102536 **12.71:1**; sidebar muted #BBCBD6/#102536 **9.42:1**;
light secondary #526277/#F1F5F9 **5.68:1**; dark text #EDF2F7/#142334 **14.13:1**;
dark secondary #BFCCD9/#142334 **9.74:1**. Typography sizes/family and navigation
hover/edge/border/focus colors are tokens alongside the spacing/shape palette.


## Bundle C login presentation

The existing QA login reuses V1 navy/green, surfaces, spacing, shape, focus, primary
Button and input styling. Original NADI artwork is rendered on the existing white
logo-surface token without recoloring or replacement. New form controls target 48 px;
required guidance, generic error, loading and expired-session states retain textual
meaning. Tablet/mobile collapse decorative copy and preserve accessible form order.
[Readiness evidence](reliability-cockpit/docs/nadi-ux-bundle-c.md) records comparison
and tests. This is a visual candidate, not global authentication activation or final
brand/token/PO accessibility certification.

## Indonesian presentation — NADI-UX-ID-01

V1 mempertahankan token navy/hijau, logo asli, tema terang/gelap, ukuran navigasi,
state fokus dan makna warna. Copy memakai Bahasa Indonesia; dictionary source-key
bertipe `idText` dan mapping `statusLabel` berada di `web/lib/id-copy.ts` serta
`id-messages.json`. Jangan gunakan label terjemahan sebagai key tab, value form,
URL, API command atau isi rekam. Option memiliki value asli yang terpisah dari label.
Kode yang tidak dikenal dan nilai sumber/pengguna tetap verbatim.

Kalimat panjang harus membungkus secara wajar; filter/action dapat wrap. Tabel
integrasi memakai TableFrame yang dapat discroll dengan keyboard, bukan memperlebar
halaman. Glosarium memakai grid responsif dengan label Inggris eksplisit dan
anchor istilah. Bantuan contextual menjelaskan persetujuan rekam ≠ izin pekerjaan.

[Evidence 1440/768/390](reliability-cockpit/docs/evidence/nadi-ux-id-01/README.md)
memakai komponen kandidat dan fixture bertanda QA SINTETIS, tanpa server kedua.
Pengujian kontras V1 dan nama aksesibel tidak merupakan sertifikasi aksesibilitas
menyeluruh. Pilihan padanan bahasa dan kepadatan halaman tetap menunggu review PO.


## Fullscreen authentication layout — NADI-UX-LOGIN-01

Login uses a standalone full-viewport navy/surface composition, unchanged logo and Indonesian form. At 768/390 the brand contracts and the form remains primary. ThemeProvider shares the existing light/dark preference with the workspace; the login theme button is independent of its topbar. QA identity stays visible; technical provenance remains on the status endpoint and workspace banner. Form h1, persistent labels, focus feedback, password toggle and 48px controls retain V1 tokens. No global authentication enforcement is introduced.

[Implementation, boundaries and evidence](reliability-cockpit/docs/nadi-ux-login-01.md).

## PdM native entry — 2026-10-13 candidate

The native multi-point form reuses V1 tokens and primitives, with 44px labeled
controls, fieldset legends, keyboard Tab order, explicit validation feedback and
neutral record states. Desktop scrolls only inside the grid; at 768px rows become
two-column grouped cards and at 390px single-column cards. The raw-sample plot uses
informational color with exact-value/time table alternatives, never severity colors
or connecting interpolation. Light/dark and responsive evidence remains isolated:
[PdM review](reliability-cockpit/docs/nadi-pdm-center-input-01.md). PO visual review
and full accessibility certification are separate pending gates.

## Workbook header candidates — 2026-10-15

Input Pengukuran reuses V1 cards, neutral pending labels, fieldsets, buttons and
scroll-contained measurement rows. The candidate source panel uses auto-fit desktop
cards for literal header/unit labels and separate unresolved notes; no engineering
severity colors. Units remain explicit and missing values remain UNKNOWN/null.
Replacement confirmation preserves unsaved readings; applying a candidate does not
edit an existing revision. [1440/1920 light/dark component evidence](reliability-cockpit/docs/evidence/nadi-pdm-workbook-01/README.md)
is synthetic, not live or Product Owner acceptance. No new token system is introduced.

## PdM desktop workbook candidates — WORKBOOK-02

Panel kandidat memakai token/grid V1 existing dan selector keluarga eksplisit; label axis sumber terlihat tanpa canonical point binding. Unit ambigu tampil BELUM DIKETAHUI, nilai awal UNKNOWN/null, pending approval bukan severity. [24 screenshot sintetis 1440/1920 light/dark](reliability-cockpit/docs/evidence/nadi-pdm-workbook-02/README.md) adalah evidence komponen, bukan live acceptance.


## NADI V2 — 2026-10-18 candidate

Incremental workspace presentation now uses navy identity, focused teal accents,
neutral surfaces and green primary actions. Shared controls have 44px minimum
height, clear focus, explicit secondary/tertiary/destructive hierarchy and busy
semantics. Labeled search and native help disclosures reduce visual noise without
removing source limitations. Forms, tables, textual statistic cards, timelines and
responsive follow-up queues share the same treatment. The scoped enterprise layer
preserves the approved standalone login. No health thresholds or color-based
condition inference were added.

Implementation and automated regression complete in the isolated V2 candidate;
PO acceptance and live integration remain pending. See the
[V2 report and matched screenshots](reliability-cockpit/docs/NADI-UX-V2-OVERHAUL-01.md).

## PdM source-history candidate — 21 October 2026

Reuse existing section, feedback, button and scrollable-table primitives for
provisional source history. Show workbook/sheet/date/status before hashes; retain
raw proofs in explicit details. Unknown unit/date/mapping remains visible; empty
values differ from zero. Byte-bounded field paging and mobile wrapping preserve
access to long proofs. No new global tokens or chart semantics are approved.
[Candidate UI/evidence](reliability-cockpit/docs/nadi-pdm-complete-history-01.md).

## PdM simplification Sprint 1 — 31 October 2026 candidate

Reuse the accepted Experience foundation: five primary links and existing utility
navigation, compact population/page facts, continuous A–D editor sections and
contextual disclosures. Input Pengukuran is the register's primary action; review
uses an explicit decision and server-authorized action. Existing neutral pending/
unknown/provisional semantics remain. [Synthetic responsive/light-dark evidence](reliability-cockpit/docs/evidence/nadi-pdm-simplification-sprint-01/README.md)
is candidate review material; PO visual acceptance and runtime activation are pending.

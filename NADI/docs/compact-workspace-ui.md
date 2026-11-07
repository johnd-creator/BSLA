# Compact workspace UI

The November 2026 UI audit keeps the existing navy/teal Laravel workspace and
compact operational tables. It changes presentation and navigation only; source
contracts, local draft ownership, role gates and validation rules are unchanged.

## Shared patterns

- Navigation groups distinguish workspace, maintenance, and data/report tasks.
  Existing links and server-side permissions remain authoritative.
- Search is the main filter action. Advanced filters use native disclosures on
  narrow screens, stay visible when active, and retain URL state. Removable
  filter chips clear pagination while preserving the other filters.
- Data tables keep their real column/row semantics. Overflowing tables get a
  named, keyboard-focusable scroll region and a visible horizontal-scroll hint.
  Empty tables fit the content width. Primary record lists keep headers visible
  during vertical scrolling.
- Pagination uses bounded previous/next controls and a human page/range summary.
  It fits the available content width even when a desktop sidebar is present.
- Forms have linked error summaries, messages beside fields, retained input,
  and Indonesian validation labels. The Indonesian validation catalog is also
  used when the host retains Laravel's default English locale; no application
  locale, date/time interpretation or validation rule is changed.
- Optional inspection findings and recommendations open progressively. Required
  request details remain visible. Sticky local-save actions include keyboard
  scroll clearance for native disclosure controls and prevent duplicate clicks.
- Asset details group recording actions separately from history links, retain
  explicit unavailable reliability states, and disclose technical identifiers.
  Existing generic asset illustrations retain their non-photo warning.
- Short scope/availability warnings remain beside data. Longer methodology is
  available in native disclosures. Missing data is never rendered as a health
  score, source synchronization claim, confirmed failure or zero risk.

The slash key focuses search when focus is outside editable controls. Its cue is
shown beside Master Asset search. Navigation, filters, disclosures and forms
remain server-rendered and usable without JavaScript.

## Decorative card accents

Summary cards use local, noninteractive SVG line drawings for asset inventory,
WO documents, measuring instruments and inspection. Work-panel headings use
matching small marks. These are decorative category motifs, not photographs,
measurements, trends, completion marks or health states. The decorative SVGs are
hidden from assistive technology and do not consume layout space or intercept
pointer input. Text, source links, unavailable states and card density remain
unchanged. Mobile artwork is smaller and lighter; no bitmap download or motion
is added.

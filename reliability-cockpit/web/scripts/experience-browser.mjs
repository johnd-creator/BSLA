// Actual React components; every request is intercepted. SYNTHETIC evidence only.
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { browserBundle } from "./localization-browser-build.mjs";
const { chromium } = await import(
  process.env.NADI_PLAYWRIGHT_MODULE
    ? pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href
    : "playwright"
);
const Axe = process.env.NADI_AXE_MODULE
  ? (await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default
  : null;
const out = resolve(
  process.env.NADI_BROWSER_OUTPUT ?? "/tmp/nadi-experience-evidence",
);
mkdirSync(out, { recursive: true });
const baseline = process.env.NADI_EXPERIENCE_BASELINE === "1",
  base = "https://experience.synthetic.invalid";
const bundle = await browserBundle(),
  browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1086 },
  }),
  page = await ctx.newPage();
const fixture = JSON.parse(readFileSync("fixtures/ux-bundle-b.json")),
  overview = JSON.parse(readFileSync("fixtures/executive-overview.json"));
const copy = JSON.parse(readFileSync("lib/id-messages.json")),
  t = (k) => copy[k] ?? k;
const asset = fixture.asset.canonical_id,
  now = "2026-10-11T08:00:00+07:00",
  checks = [],
  errors = [],
  requests = [],
  violations = [];
let newerCaseRevision = false;
const cases = [
  "DEMO — telaah pengukuran motor",
  "DEMO — variasi konteks akuisisi",
  "DEMO — verifikasi rujukan evidence",
  "DEMO — pemeriksaan lanjutan",
].map((title, i) => ({
  case_id: "case:DEMO-00" + (i + 1),
  title,
  problem_statement:
    "SYNTHETIC — Apakah perbedaan konteks akuisisi memengaruhi keterbandingan pengukuran?",
  canonical_asset_id: asset,
  category: "INVESTIGATION",
  priority: i === 0 ? "HIGH" : "NORMAL",
  assigned_engineer: "demo-engineer",
  created_by: "demo-engineer",
  status: i === 2 ? "IN_REVIEW" : "DRAFT",
  revision: 3,
  updated_at: now,
  investigation: {
    operating_context:
      "SYNTHETIC — beban dan konteks operasi dilaporkan inspector; bukan bukti pembangkit.",
    observed_symptoms: ["SYNTHETIC — observasi berulang pada titik yang sama."],
    observations: [
      "SYNTHETIC — nilai nol tercatat; parameter kedua belum diketahui.",
    ],
    hypotheses: [
      "SYNTHETIC — perbedaan akuisisi mungkin berpengaruh; belum tervalidasi.",
    ],
    open_questions: [
      "Apakah identitas titik dan instrumen sudah dikonfirmasi?",
    ],
    proposed_next_checks: ["Konfirmasi konteks sebelum membandingkan seri."],
  },
  review: null,
  evidence: [
    {
      reference_id: "reference:DEMO-001",
      kind: "MANUAL_INSPECTION",
      record_id: fixture.inspections[0].record_id,
      mode: "FROZEN_SNAPSHOT",
      stable_version: "SYNTHETIC-r3-sha256",
      source_timestamp: fixture.inspections[0].inspected_at,
      snapshot: {
        label: "DEMO — snapshot inspeksi",
        availability: "AVAILABLE",
      },
    },
  ],
  notes: [
    {
      text: "SYNTHETIC — konteks dicatat terpisah dari hipotesis.",
      actor: "demo-engineer",
    },
  ],
}));
const pageOf = (items,u) => {
 const offset=Number(u?.searchParams.get('offset')??0),limit=Number(u?.searchParams.get('limit')??25);
 return {items:items.slice(offset,offset+limit),total:items.length,offset,limit,has_more:offset+limit<items.length,filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'INSPECTED_AT'};
};
const check = (name, value) => {
  assert.ok(value, name);
  checks.push(name);
};
await ctx.route("**/*", async (route) => {
  const r = route.request(),
    u = new URL(r.url()),
    p = u.pathname;
  requests.push({
    path: p,
    query: u.search,
    method: r.method(),
    ...(r.method() !== "GET" ? { body: r.postDataJSON() } : {}),
  });
  if (u.origin !== base) return route.abort("blockedbyclient");
  if (p === "/candidate.js")
    return route.fulfill({
      contentType: "application/javascript",
      body: bundle.js,
    });
  if (p === "/candidate.css")
    return route.fulfill({ contentType: "text/css", body: bundle.css });
  if (p === "/logo_nadi.png")
    return route.fulfill({
      contentType: "image/png",
      body: readFileSync("public/logo_nadi.png"),
    });
  if (r.isNavigationRequest())
    return route.fulfill({
      contentType: "text/html",
      body: '<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SYNTHETIC NADI design comparison</title><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>',
    });
  if (p.includes("decision-overview")) return route.fulfill({ json: overview });
  if (p.startsWith("/api/engineering-qa/")) {
    const [resource, encoded, action] = p
        .slice("/api/engineering-qa/".length)
        .split("/"),
      id = decodeURIComponent(encoded ?? "");
    if (resource === "session")
      return route.fulfill({
        json: {
          subject: "demo-engineer",
          roles: ["AUTHOR"],
          asset_ids: [asset],
          csrf_token: "SYNTHETIC_NOT_A_SESSION",
        },
      });
    if (resource === "asset-context")
      return route.fulfill({
        json: {
          canonical_asset_id: asset,
          identity_availability: "AVAILABLE",
          identity: {
            description: "DEMO Motor 1 · QA SINTETIS",
            location_ref: "DEMO location",
          },
        },
      });
    if (action === "history")
      return route.fulfill({
        json: [
          {
            revision: 3,
            actor: "demo-engineer",
            action: "UPDATE",
            occurred_at: now,
            reason: "SYNTHETIC — observasi diperjelas",
          },
          {
            revision: 2,
            actor: "demo-engineer",
            action: "EVIDENCE",
            occurred_at: now,
            reason: "SYNTHETIC — snapshot exact",
          },
          {
            revision: 1,
            actor: "demo-engineer",
            action: "CREATE",
            occurred_at: now,
            reason: "SYNTHETIC — draf awal",
          },
        ],
      });
    const rows =
      resource === "cases"
        ? cases
        : resource === "inspections"
          ? fixture.inspections
          : [];
    if (r.method() !== "GET")
      return route.fulfill({
        status: 409,
        json: { detail: { code: "SYNTHETIC_CONFLICT" } },
      });
    let result = rows;
    if (u.searchParams.get("status"))
      result = result.filter((x) => x.status === u.searchParams.get("status"));
    if (u.searchParams.get("method"))
      result = result.filter((x) => x.method === u.searchParams.get("method"));
    if (u.searchParams.get("search"))
      result = result.filter((x) =>
        JSON.stringify(x).includes(u.searchParams.get("search")),
      );
    return route.fulfill({
      json: id
        ? {...rows.find((x) => (x.case_id ?? x.record_id) === id),...(resource==="cases"&&newerCaseRevision?{revision:4}:{})}
        : pageOf(result,u),
    });
  }
  return route.fulfill({ status: 404, body: "" });
});
page.on("pageerror", (e) => errors.push(e.message));
const button = (name) => page.getByRole("button", { name, exact: true });
const go = async (path) => {
  await page.goto(base + path, { waitUntil: "networkidle" });
  await page.locator(".loading-state").waitFor({ state: "hidden" });
};
async function editor() {
  await go("/pdm");
  await button("Input Pengukuran").click();
  await page
    .getByLabel("Versi metode / prosedur")
    .fill("SYNTHETIC-candidate-v1");
  await page.getByLabel("Waktu inspeksi asli").fill(now);
  for (let i = 1; i <= 3; i++) {
    if (i > 1) await button("Tambah baris").click();
    await page
      .getByLabel("Titik " + i, { exact: true })
      .fill("point:DEMO-" + i);
    await page
      .getByLabel("Parameter " + i, { exact: true })
      .fill("DEMO velocity");
    await page
      .getByLabel("Tipe nilai " + i, { exact: true })
      .selectOption(i === 3 ? "UNKNOWN" : "NUMERIC");
    if (i < 3)
      await page
        .getByLabel("Nilai asli " + i, { exact: true })
        .fill(i === 1 ? "0" : "4.2");
    await page.getByLabel("Unit asli " + i, { exact: true }).fill("mm/s");
    await page
      .getByLabel("Waktu measurement " + i, { exact: true })
      .fill(i === 3 ? "" : now);
  }
  await page
    .getByLabel("Observasi (satu per baris)")
    .fill("SYNTHETIC — titik kedua perlu konfirmasi konteks.");
}
const screens = [
  ["executive", () => go("/")],
  ["pdm", () => go("/pdm")],
  ["measurement", editor],
  ["cases", () => go("/engineering/cases")],
  ["case-detail", () => go("/engineering/cases?record=case%3ADEMO-001")],
];
try {
  for (const width of (process.env.NADI_BROWSER_WIDTHS ?? "1440,1920,768,390")
    .split(",")
    .map(Number))
    for (const theme of ["light", "dark"])
      for (const [name, open] of screens) {
        await page.setViewportSize({ width, height: 1086 });
        await open();
        await page.evaluate((t) => {
          document.documentElement.dataset.theme = t;
          document.activeElement?.blur();
          window.scrollTo(0, 0);
        }, theme);
        // Wait for actual theme transitions to finish before measuring contrast or capturing.
        await page.evaluate(()=>Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{}))));
        check(
          "no page overflow " + name + width + theme,
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        );
        check(
          "one main " + name + width + theme,
          (await page.getByRole("main").count()) === 1,
        );
        if (Axe && !baseline) {
          const result = await new Axe({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
            .analyze();
          violations.push(
            ...result.violations.map((v) => ({
              screen: name,
              width,
              theme,
              id: v.id,
              nodes: v.nodes.map((n) => ({
                target: n.target,
                summary: n.failureSummary,
              })),
            })),
          );
        }
        await page.screenshot({
          path: out + "/" + name + "-" + theme + "-" + width + ".png",
          fullPage: true,
        });
      }
  if (!baseline) {
    await page.setViewportSize({ width: 1440, height: 1086 });
    await go("/");
    await page.getByLabel(t("Maintenance activity window")).selectOption("90");
    await page.locator(".loading-state").waitFor({ state: "hidden" });
    check(
      "period control issues the existing 90-day query",
      requests.some(
        (r) => r.path.includes("decision-overview") && r.query.includes("90"),
      ),
    );
    await button("Tampilkan semua 7 aset").click();
    check(
      "concentration expands to exact seven fixture assets",
      (await page.locator(".executive-evidence-grid tbody tr").count()) === 7,
    );
    await button(t("Show top 5 assets")).click();
    check(
      "concentration returns to five rows",
      (await page.locator(".executive-evidence-grid tbody tr").count()) === 5,
    );
    await go("/engineering/cases");
    await page
      .getByLabel("Cari pada halaman Case ini")
      .fill("konteks akuisisi");
    check(
      "Case page-local search narrows the loaded register",
      (await page.locator(".case-register tbody tr").count()) === 1,
    );
    await page.getByLabel("Cari pada halaman Case ini").fill("");
    await button(cases[0].title).click();
    check(
      "selection focuses the Case detail pane",
      await page
        .locator("#case-record-pane")
        .evaluate((n) => n === document.activeElement),
    );
    check(
      "selection retains the exact deep link",
      new URL(page.url()).searchParams.get("record") === cases[0].case_id,
    );
    await button(t("Edit case")).click();
    await page.locator("#case-title").fill("SYNTHETIC — draft stays mounted");
    await button("Evidence").click();
    check(
      "section jump focuses source evidence",
      await page
        .locator("#case-evidence")
        .evaluate((n) => n === document.activeElement),
    );
    check(
      "section navigation preserves unsaved Case input",
      (await page.locator("#case-title").inputValue()) ===
        "SYNTHETIC — draft stays mounted",
    );
    const nav = page.locator(".record-navigator");
    await nav.locator("summary").click();
    await nav.locator("summary").click();
    check(
      "collapsing record navigation preserves the edit form",
      (await page.locator("#case-title").inputValue()) ===
        "SYNTHETIC — draft stays mounted",
    );
    page.once("dialog", (d) => d.dismiss());
    await page.locator(".record-nav-item").nth(1).click();
    check(
      "cancelled Case selection preserves draft and exact selection",
      (await page.locator("#case-title").inputValue()) ===
        "SYNTHETIC — draft stays mounted" &&
        new URL(page.url()).searchParams.get("record") === cases[0].case_id,
    );
    newerCaseRevision=true;
    await button(t("Read latest revision (keep unsaved form)")).click();
    await page.locator('.case-detail > .section-note').filter({hasText:'Revisi 4'}).waitFor();
    check(
      "latest read preserves original Case edit base",
      (await page.locator("#case-title").inputValue()) ===
        "SYNTHETIC — draft stays mounted",
    );
    await button(t("Save case")).click();
    await page
      .getByRole("alert")
      .filter({ hasText: "SYNTHETIC_CONFLICT" })
      .waitFor();
    check(
      "conflict preserves the unsaved form and original expected revision",
      (await page.locator("#case-title").inputValue()) ===
        "SYNTHETIC — draft stays mounted" &&
        requests.findLast((r) => r.method === "PUT").body.expected_revision ===
          3,
    );
    page.once("dialog", (d) => d.accept());
    await button(t("Cancel form")).click();
    await button(t("Read case history")).click();
    await page.getByRole('region',{name:'Riwayat revisi Case',exact:true}).waitFor();
    check(
      "exact revision history remains readable",
      (await page
        .getByRole("region", { name: "Riwayat revisi Case", exact: true })
        .locator("tbody tr")
        .count()) === 3,
    );
    await button("Kembali ke register").click();
    check(
      "back to Case register clears deep link",
      !new URL(page.url()).searchParams.has("record") &&
        (await page.locator(".case-register").isVisible()),
    );
    await go("/pdm");
    await page
      .getByLabel("Cari inspeksi / observasi")
      .fill("no-synthetic-match");
    await button("Terapkan filter server").click();
    await page
      .getByText("Tidak ada inspeksi dalam filter server ini.", { exact: true })
      .waitFor();
    check("PdM search remains server-authoritative", true);
    await button("Hapus filter").click();
    await page.locator(".record-open").first().waitFor();
    check(
      "reset restores authorized PdM population",
      (await page.locator(".record-open").count()) ===
        fixture.inspections.length,
    );
    await page.locator(".record-open").first().click();
    check(
      "inspection selection focuses detail",
      await page
        .locator("#pdm-record-pane")
        .evaluate((n) => n === document.activeElement),
    );
    check(
      "inspection deep link keeps original record identity",
      new URL(page.url()).searchParams.get("record") ===
        fixture.inspections[0].record_id,
    );
    await button("Register Inspeksi").click();
    check(
      "Register action restores list",
      await page.locator(".pdm-register").isVisible(),
    );
    await editor();
    await page.locator(".editor-index a").nth(1).click();
    check(
      "editor jump retains raw zero",
      (await page.getByLabel("Nilai asli 1", { exact: true }).inputValue()) ===
        "0",
    );
    check(
      "unknown reading remains disabled and empty",
      (await page.getByLabel("Nilai asli 3", { exact: true }).isDisabled()) &&
        (await page
          .getByLabel("Nilai asli 3", { exact: true })
          .inputValue()) === "",
    );
    page.once("dialog", (d) => d.dismiss());
    await button("Register Inspeksi").click();
    check(
      "cancelled editor leave retains continuous draft",
      (await page.getByLabel("Nilai asli 1", { exact: true }).inputValue()) ===
        "0",
    );
    page.once("dialog", (d) => d.accept());
    await button("Batal input").click();
    check(
      "explicit editor cancel returns to register",
      await page.locator(".pdm-register").isVisible(),
    );
    check(
      "no self-review exposed on authored Case",
      (await button(t("Approve case")).count()) === 0,
    );
    check(
      "synthetic requests never target production",
      requests.every((r) => !r.path.includes("oslc")),
    );
  }
  check("no browser exceptions", errors.length === 0);
  check("automated WCAG A/AA", violations.length === 0);
  writeFileSync(
    out + "/results.json",
    JSON.stringify(
      {
        label: "SYNTHETIC actual React components; no live data or runtime",
        baseline,
        checks,
        errors,
        violations,
        requests,
      },
      null,
      2,
    ),
  );
  console.log("Experience browser PASS " + checks.length + " checks");
} catch (e) {
  writeFileSync(
    out + "/failure.json",
    JSON.stringify({ message: e.message, errors, violations }, null, 2),
  );
  if(!page.isClosed())await page.screenshot({ path: out + "/failure.png", fullPage: true });
  throw e;
} finally {
  await browser.close();
  rmSync(bundle.temp, { recursive: true, force: true });
}

import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, symlinkSync, readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
const require = createRequire(import.meta.url);
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const temp = mkdtempSync(join(tmpdir(), "nadi-ux-"));
let checks = 0;
const test = (label, fn) => { fn(); checks++; console.log(`PASS ${label}`); };
try {
  const files = ["components/ui.tsx", "lib/navigation.ts", "lib/overview.ts", "lib/product-records.ts", "components/ExecutiveOverview.tsx", "components/AssetHealthSummary.tsx", "components/InspectionDetail.tsx", "components/RecommendationDetail.tsx"].filter(existsSync);
  execFileSync(process.execPath, ["node_modules/typescript/bin/tsc", ...files, "--outDir", temp, "--rootDir", ".", "--module", "commonjs", "--target", "ES2022", "--jsx", "react-jsx", "--esModuleInterop", "--skipLibCheck", "--resolveJsonModule", "--moduleResolution", "node"], { stdio: "pipe" });
  symlinkSync(resolve("node_modules"), join(temp, "node_modules"));
  const ui = require(join(temp, "components/ui.js"));
  const copy=JSON.parse(readFileSync("lib/id-messages.json","utf8"));
  const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
  test("scrollable table keeps minimum width inside outer region", () => {
    const html = render(ui.TableFrame, { minWidth: 900, children: React.createElement("table") });
    assert.match(html, /role="region"[^>]+tabindex="0"><div[^>]+min-width:900px/);
    assert.doesNotMatch(html.split("><div")[0], /min-width/);
  });
  test("loading announces progress without a temporary value", () => assert.match(render(ui.LoadingState), /role="status"/));
  test("errors are announced and retry remains optional", () => {
    assert.match(render(ui.ErrorState, { onRetry() {} }), /role="alert"/);
    assert.match(render(ui.ErrorState, { onRetry() {} }), /Coba lagi/);
  });
  test("unknown raw source status stays neutral", () => assert.match(render(ui.StatusBadge, { value: "UNKNOWN", mode: "raw-neutral" }), /neutral[^>]*>Belum diketahui \(UNKNOWN\)/));
  test("raw CLOSED source status is not a health classification", () => assert.match(render(ui.StatusBadge, { value: "CLOSED", mode: "raw-neutral" }), /neutral/));
  test("legacy pages keep one main landmark and contained tables", () => {
    for(const path of ["app/(workspace)/work-orders/page.tsx", "app/(workspace)/equipment/[id]/page.tsx"]) {
      const source=readFileSync(path,"utf8"); assert.ok(!source.includes("<main>")); assert.ok(source.includes("<TableFrame"));
    }
  });
  test("legacy equipment protects identity from late responses and unknown totals", () => {
    const source=readFileSync("app/(workspace)/equipment/[id]/page.tsx","utf8");
    assert.match(source,/if \(!active\) return/); assert.ok(source.includes('workOrders?.total ?? statusLabel("UNKNOWN")')); assert.ok(source.includes('if (loading)'));
  });
  test("busy button prevents duplicate activation and announces progress", () => {
    const html = render(ui.Button, { busy: true, children: "Menyimpan…" });
    assert.match(html, /disabled=""/); assert.match(html, /aria-busy="true"/); assert.match(html, /aria-hidden="true"/);
  });
  test("search field retains label and supplied controlled input value", () => {
    const html = render(ui.SearchField, { id: "case-search", label: "Cari Case", value: "asset:A", readOnly: true });
    assert.match(html, /for="case-search"/); assert.match(html, /type="search"/); assert.match(html, /value="asset:A"/);
  });
  test("extended help uses a native keyboard disclosure", () => {
    const html = render(ui.HelpDetails, { title: "Dasar waktu", children: "Timestamp asli" });
    assert.match(html, /<details/); assert.match(html, /<summary>Dasar waktu/); assert.match(html, /Timestamp asli/);
  });
  test("button does not submit a form accidentally", () => assert.match(render(ui.Button, { children: "Review" }), /type="button"/));
  test("breadcrumb declares exactly one current page", () => assert.equal((render(ui.Breadcrumbs, {items:[{label:"NADI"},{label:"Overview"}]}).match(/aria-current="page"/g) ?? []).length, 1));
  test("input has persistent associated label", () => assert.match(render(ui.InputControl, { id: "scope", label: "Scope" }), /for="scope"/));
  const records=require(join(temp,"lib/product-records.js"));
  test("original measurement preserves zero false and unknown distinctly",()=>{assert.equal(records.originalValue(0),"0");assert.equal(records.originalValue(false),"false");assert.equal(records.originalValue(null),"UNKNOWN");});
  test("page filters use exact canonical identity and local status",()=>{const row={canonical_asset_id:"asset:A",status:"APPROVED"};assert.equal(records.recordMatches(row,"asset:A","APPROVED","sample","Sample"),true);assert.equal(records.recordMatches(row,"asset:B","","",""),false);assert.equal(records.recordMatches(row,"","DRAFT","",""),false);});
  test("page counts reconcile with only provided authorized records",()=>{assert.deepEqual(records.pageCounts([{status:"DRAFT"},{status:"APPROVED"},{status:"DRAFT"}]),{DRAFT:2,APPROVED:1});assert.deepEqual(records.pageCounts([]),{});});
  test("record links encode identity and exclude commands",()=>{assert.equal(records.qaRecordLink("cases","case:A"),"/engineering/cases?record=case%3AA");assert.ok(!records.validRecordId("../other"));assert.ok(records.validRecordId("inspection:1"));});
  test("candidate methods never equate PD and DGA",()=>assert.deepEqual(records.candidateMethods.map(x=>x.id),["VIBRATION","IR_THERMOGRAPHY","MCSA","TRIBOLOGY"]));
  const fixture=JSON.parse(readFileSync("fixtures/ux-bundle-b.json","utf8"));
  const AssetSummary=require(join(temp,"components/AssetHealthSummary.js")).default;
  const InspectionDetail=require(join(temp,"components/InspectionDetail.js")).default;
  const RecommendationDetail=require(join(temp,"components/RecommendationDetail.js")).default;
  test("asset summary renders reference sections with unsupported scores explicit",()=>{const html=render(AssetSummary,{asset:fixture.asset,context:null,maintenanceCount:null,assessmentCount:0,onMaintenance(){}});for(const name of [copy["Technical Details"],copy["PdM Condition Summary"],copy["Maintenance / Work Order History"],copy["Recommendations / Actions"],"NOT ASSESSED","UNKNOWN"])assert.ok(html.includes(name), name);assert.ok(html.includes(copy["Operational recommendation linkage UNAVAILABLE"]));});
  test("inspection keeps original sample context, time, units and review separate",()=>{const html=render(InspectionDetail,{row:fixture.inspections[0]});for(const x of ["mm/s","2026-10-01T07:00:00Z","point:DEMO-DE","Observasi","Interpretasi engineering","Review independen","METADATA_ONLY_NOT_UPLOADED"])assert.ok(html.includes(x));assert.ok(!html.includes('href="attachment:'));});
  test("recommendation completion never becomes verified effectiveness",()=>{const html=render(RecommendationDetail,{row:fixture.recommendations[2]});assert.ok(html.includes("NOT VERIFIED"));assert.ok(html.includes("NOT LINKED"));assert.ok(html.includes("Review rekam" )||html.includes("Review rekam independen"));});
  test("engineering text is escaped, not rendered as executable HTML",()=>{const html=render(RecommendationDetail,{row:{...fixture.recommendations[0],rationale:'<script>alert(1)</script>'}});assert.ok(html.includes("&lt;script&gt;"));assert.ok(!html.includes("<script>"));});
  test("production product routes cannot request isolated QA records",()=>{for(const path of ["app/(workspace)/pdm/page.tsx","app/(workspace)/recommendations/page.tsx","app/(workspace)/action-board/page.tsx"])assert.ok(readFileSync(path,"utf8").includes('process.env.NODE_ENV==="development"&&process.env.NADI_ENGINEERING_QA_ENABLED==="true"'));});
  const css = readFileSync("app/design-tokens.css", "utf8");
  const luminance = hex => {
    const rgb = hex.match(/\w\w/g).map(x => parseInt(x, 16) / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4);
    return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
  };
  for (const [theme, section] of [["light", css.split(':root[data-theme')[0]], ["dark", css.split(':root[data-theme')[1]]]) {
    const token = name => section.match(new RegExp(`--${name}: #([a-f0-9]{6})`))[1];
    for (const [fg, bg] of [["text", "surface"], ["muted", "surface"], ["muted-2", "surface-2"], ["primary", "surface"], ["button-text", "primary"], ["sidebar-text", "sidebar"], ["sidebar-muted", "sidebar"], ["amber", "surface"]].filter(([fg]) => theme === "light" || !fg.startsWith("sidebar"))) {
      test(`${theme} ${fg}/${bg} contrast >= 4.5`, () => {
        const a = luminance(token(fg)), b = luminance(token(bg));
        assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05) >= 4.5);
      });
    }
  }
  if (existsSync(join(temp, "lib/navigation.js"))) {
    const { navigation, utilityNavigation, routeMatches, navigationGroup } = require(join(temp, "lib/navigation.js"));
    test("five primary work entries are exact and stable",()=>assert.deepEqual(navigation.map(x=>[x.label,x.href]),[["Beranda","/"],["Aset","/assets"],["PdM Center","/pdm"],["Tindak Lanjut","/action-board"],["Laporan","/reports"]]));
    test("all existing navigation URLs survive", () => {
      const hrefs = [...navigation,...utilityNavigation].flatMap(x => x.children?.map(c => c.href) ?? [x.href]);
      for (const href of ["/", "/assets", "/asset-health", "/maintenance", "/maintenance/investigation", "/work-orders", "/fmea", "/rcfa", "/overhauls", "/data-quality"]) assert.ok(hrefs.includes(href), href);
    });
    test("route boundary prevents false active links", () => { assert.ok(!routeMatches("/assets-other", "/assets")); assert.ok(routeMatches("/assets/id", "/assets")); assert.ok(!routeMatches("/assets", "/")); });
    test("detail routes retain domain context", () => { assert.equal(navigationGroup("/assets/A%3AB"), "assets"); assert.equal(navigationGroup("/equipment/42"), "asset-records"); assert.equal(navigationGroup("/maintenance/investigation"), "asset-records"); });
    test("planned modules cannot silently redirect", () => { for(const item of [...navigation,...utilityNavigation].filter(x => x.planned)) { assert.equal(item.href, undefined); assert.equal(item.children, undefined); } });
  }
  if (existsSync(join(temp, "lib/overview.js"))) {
    const { factualMetric, overviewDate, attentionItems } = require(join(temp, "lib/overview.js"));
    test("unknown and gated numbers cannot become facts", () => { for(const x of [null, undefined, NaN, Infinity]) assert.equal(factualMetric({value:x,evidence_class:"VERIFIED"}), "UNKNOWN"); assert.equal(factualMetric({value:62,evidence_class:"BUSINESS_SEMANTICS_REQUIRED"}), "NOT ASSESSED"); assert.equal(factualMetric({value:0,evidence_class:"VERIFIED"}), "0"); });
    test("invalid/missing timestamps are unknown", () => { for(const x of [null, "not-a-date"]) assert.equal(overviewDate(x), "UNKNOWN"); });
    test("attention shows exact integrity counts, no risk math", () => {
      const items = attentionItems({registered_assets_unresolved:0,asset_refs_unresolved:3,workorder_refs_unresolved:2});
      assert.deepEqual(items.map(x => x.count), [0,3,2]);
      assert.ok(items.every(x => x.href === "/data-quality"));
    });
  }
  if (existsSync(join(temp, "components/ExecutiveOverview.js"))) {
    const { ActivityChart, Distribution } = require(join(temp, "components/ExecutiveOverview.js"));
    test("chart preserves exact zero, unknown and dated values", () => {
      const rows = [0, null, 12].map((value, i) => ({period_start:`2026-10-0${i+1}T00:00:00Z`, period_end:`2026-10-0${i+2}T00:00:00Z`, event_count:{value,evidence_class:"DERIVED_SAFE"}}));
      const html = render(ActivityChart,{rows});
      assert.match(html, /UNKNOWN/); assert.match(html, /height:0%/); assert.match(html, /height:100%/); assert.match(html, /Lihat periode dan jumlah persis/);
    });
    test("empty distributions and trend explain absence", () => { assert.ok(render(ActivityChart,{rows:[]}).includes(copy["An empty activity series does not establish equipment condition."])); assert.match(render(Distribution,{title:"statuses", rows:[]}), /Belum ada statuses/); });
  }
  console.log(`UX checks passed: ${checks}`);
} finally { rmSync(temp, {recursive:true,force:true}); }

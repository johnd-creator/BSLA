import { idText } from "./id-copy";
export interface NavLink { href: string; label: string; section?: string; }
export interface NavItem { id: string; label: string; icon: string; href?: string; children?: NavLink[]; planned?: boolean; engineeringOnly?: boolean; }

/** Five everyday entry points. Utility routes remain separate, not removed. */
export const navigation: NavItem[] = [
  { id: "overview", href: "/", label: "Beranda", icon: "overview" },
  { id: "assets", href: "/assets", label: "Aset", icon: "assets" },
  { id: "pdm", href: "/pdm", label: "PdM Center", icon: "chart" },
  { id: "actions", href: "/action-board", label: "Tindak Lanjut", icon: "board" },
  { id: "reports", href: "/reports", label: "Laporan", icon: "report" },
];
export const utilityNavigation: NavItem[] = [
  { id: "asset-records", label: "Rekam aset & maintenance", icon: "assets", children: [
    { href: "/asset-health", label: idText("Assessment Records") },
    { href: "/maintenance", label: idText("Maintenance") },
    { href: "/maintenance/investigation", label: idText("Maintenance Investigation") },
    { href: "/work-orders", label: idText("Work Orders") },
    { href: "/fmea", label: "FMEA" },
    { href: "/rcfa", label: "RCFA · register global" },
    { href: "/overhauls", label: "Overhaul" },
  ] },
  { id: "integration", label: "Integrasi & kualitas data", icon: "integration", children: [
    { href: "/system-integration", label: "Ringkasan Integrasi" },
    { href: "/data-quality", label: idText("Data Trust Center") },
  ] },
  { id: "engineering", label: "Perangkat Engineering", icon: "engineering", engineeringOnly: true, children: [
    { href: "/engineering/cases", label: "Engineering Cases" },
    { href: "/recommendations", label: "Recommendations" },
    { href: "/engineering/advisories", label: "Advisory" },
    { href: "/engineering/inbox", label: "Inbox & acknowledgement" },
    { href: "/engineering", label: "Ruang Engineering" },
    { href: "/engineering/workflow", label: "Workflow Engineering" },
    { href: "/engineering/local", label: "Rekam & audit berotorisasi" },
    { href: "/engineering/qa", label: "Engineering QA" },
    { href: "/engineering/lab", label: "Laboratorium Engineering" },
  ] },
  { id: "guide", href: "/panduan/istilah", label: "Panduan & Istilah", icon: "report" },
  { id: "administration", label: idText("Administration"), icon: "settings", planned: true },
];
export function routeMatches(path: string, href: string): boolean {
  return path === href || (href !== "/" && path.startsWith(`${href}/`));
}
export function activeLink(path: string, links: NavLink[]): string | undefined {
  return links.filter(link => routeMatches(path, link.href)).sort((a, b) => b.href.length - a.href.length)[0]?.href;
}
export function navigationGroup(path: string): string | undefined {
  if (["/engineering/cases", "/engineering/advisories", "/engineering/inbox", "/recommendations"].some(href => routeMatches(path, href))) return "actions";
  if (routeMatches(path, "/asset-health")) return "assets";
  if (routeMatches(path, "/equipment")) return "asset-records";
  return navigation.find(item => item.href && routeMatches(path, item.href))?.id
    ?? utilityNavigation.find(item => item.href ? routeMatches(path, item.href) : activeLink(path, item.children ?? []))?.id;
}

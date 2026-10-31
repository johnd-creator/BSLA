"use client";

import { idText } from "../lib/id-copy";
import Link from "next/link";
import WorkspaceAccount from "./WorkspaceAccount";
import { ThemeToggle } from "./ThemeProvider";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { activeLink, navigation, utilityNavigation, navigationGroup } from "../lib/navigation";

const iconPaths: Record<string, string> = {
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  assets: "M3 12h4l3-7 4 14 3-7h4 M4 5C9 1 12 5 12 5s3-4 8 0",
  chart: "M4 20V10 M10 20V4 M16 20v-7 M22 20H2",
  idea: "M9 18h6 M9 21h6 M8 14a6 6 0 1 1 8 0l-1 2H9z",
  board: "M8 4H4v17h16V4h-4 M8 2h8v5H8z M8 11h8 M8 16h6",
  report: "M5 2h10l4 4v16H5z M14 2v5h5 M8 11h8 M8 15h8 M8 19h5",
  integration: "M8 3h8v5H8z M2 16h7v5H2z M15 16h7v5h-7z M12 8v4 M5 16v-4h14v4",
  settings: "M9 3h6l1 4 4 1v8l-4 1-1 4H9l-1-4-4-1V8l4-1z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
  engineering: "M8 4l-5 8 5 8 M16 4l5 8-5 8 M14 4l-4 16",
};
export function NavIcon({ name }: { name: string }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={iconPaths[name] ?? iconPaths.overview} /></svg>;
}

export function AppShell({ children, engineeringVisible = false, liveDevelopment = false }: { children: ReactNode; engineeringVisible?: boolean; liveDevelopment?: boolean }) {
  const pathname = usePathname() ?? "/";
  const group = navigationGroup(pathname);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setDrawer(false);
    setExpanded(current => ({ ...current, ...Object.fromEntries(utilityNavigation.filter(item => activeLink(pathname, item.children ?? [])).map(item => [item.id, true])) }));
  }, [pathname, group]);


  useEffect(() => {
    if (!drawer) return;
    const element = sidebar.current;
    const previous = document.activeElement as HTMLElement | null;
    const trigger = menuButton.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () => Array.from(element?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? []).filter(node => node.getClientRects().length > 0);
    focusable()[0]?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setDrawer(false); }
      if (event.key === "Tab") {
        const nodes = focusable(), first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    const media = window.matchMedia("(min-width: 1024px)");
    const resize = () => { if (media.matches) setDrawer(false); };
    document.addEventListener("keydown", keyboard);
    media.addEventListener("change", resize);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", keyboard);
      media.removeEventListener("change", resize);
      (previous ?? trigger)?.focus();
    };
  }, [drawer]);

  function toggleGroup(id: string) {
    if (collapsed) { setCollapsed(false); setExpanded(current => ({ ...current, [id]: true })); }
    else setExpanded(current => ({ ...current, [id]: !current[id] }));
  }

  return <div className={`nadi-shell${liveDevelopment ? " development-shell" : ""}${collapsed ? " sidebar-collapsed" : ""}${drawer ? " drawer-open" : ""}`}>
    <a className="skip-link" href="#main-content">{idText("Skip to content")}</a>
    {drawer && <button type="button" className="drawer-backdrop" aria-label={idText("Close navigation")} onClick={() => setDrawer(false)} />}
    <aside ref={sidebar} id="nadi-sidebar" className="nadi-sidebar" role={drawer ? "dialog" : undefined} aria-modal={drawer ? true : undefined} aria-label={idText("NADI navigation panel")}>
      <div className="sidebar-brand-row"><Link href="/" className="nadi-brand" aria-label="NADI Beranda"><span className="brand-emblem" aria-hidden="true">N</span><span className="nav-copy"><strong>NADI</strong><small>{idText("Reliability Data Platform")}</small></span></Link><button type="button" className="drawer-close" aria-label={idText("Close navigation")} onClick={() => setDrawer(false)}>×</button></div>
      <nav className="nadi-nav" aria-label={idText("NADI navigation")}>
        <div className="nadi-primary-nav" role="group" aria-label="Area kerja utama">
          {navigation.map(item => <Link key={item.id} href={item.href!} className={`nav-link${group === item.id ? " active" : ""}`} aria-current={pathname === item.href ? "page" : undefined} aria-label={collapsed ? item.label : undefined} title={collapsed ? item.label : undefined}><NavIcon name={item.icon}/><span className="nav-copy">{item.label}</span></Link>)}
        </div>
        <div className="nadi-utility-nav" role="group" aria-label="Navigasi pendukung">
          <p className="nav-section-label nav-copy">Data, perangkat & bantuan</p>
        {utilityNavigation.filter(item => !item.engineeringOnly || engineeringVisible).map(item => {
          const active = group === item.id || !!activeLink(pathname, item.children ?? []);
          const open = expanded[item.id] && !collapsed;
          const currentLink = activeLink(pathname, item.children ?? []);
          const contents = <><NavIcon name={item.icon} /><span className="nav-copy">{item.label}</span></>;
          return <div key={item.id} className="nav-item">
            {item.planned ? <div className="nav-link planned" aria-disabled="true" title={`${item.label} — direncanakan`}><span className="sr-only">{collapsed ? `${item.label} — direncanakan` : ""}</span>{contents}<span className="planned-tag nav-copy">{idText("Planned")}</span></div>
              : item.href ? <Link href={item.href} className={`nav-link${active ? " active" : ""}`} aria-current={active ? "page" : undefined} aria-label={collapsed ? item.label : undefined} title={collapsed ? item.label : undefined}>{contents}</Link>
                : <button type="button" className={`nav-link nav-group${active ? " active" : ""}`} onClick={() => toggleGroup(item.id)} aria-expanded={!!open} aria-controls={`nav-${item.id}`} aria-label={collapsed ? item.label : undefined} title={collapsed ? item.label : undefined}>{contents}<span className="nav-copy nav-chevron" aria-hidden="true">{open ? "−" : "+"}</span></button>}
            {item.children && <div id={`nav-${item.id}`} className="nav-submenu" hidden={!open}>{item.children.map((link, index) => <div key={link.href}>{link.section && link.section !== item.children?.[index - 1]?.section && <p className="nav-section-label">{link.section}</p>}<Link className={`nav-sublink${currentLink === link.href ? " active" : ""}`} href={link.href} aria-current={pathname === link.href ? "page" : undefined}>{link.label}</Link></div>)}{item.id === "integration" && <div className="nav-planned-domains"><span>{idText("PI System · Planned")}</span><span>{idText("CEMS · Planned")}</span></div>}</div>}
          </div>;
        })}
        </div>
      </nav>
      <div className="sidebar-footer"><span className="nav-copy scope-label">{idText("OPERATING SCOPE")}</span><strong>BSR / IP</strong><small className="nav-copy">{idText("Controlled Reliability Mart")}</small></div>
      <button type="button" className="sidebar-collapse" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? idText("Expand sidebar") : idText("Collapse sidebar")} aria-expanded={!collapsed}><span aria-hidden="true">{collapsed ? "»" : "«"}</span><span className="nav-copy">{idText("Collapse sidebar")}</span></button>
    </aside>
    <div className="nadi-content" inert={drawer ? true : undefined}>
      <header className="nadi-topbar"><div className="topbar-context"><button ref={menuButton} type="button" className="menu-toggle icon-button" aria-label={idText("Open navigation")} aria-expanded={drawer} aria-controls="nadi-sidebar" onClick={() => { setCollapsed(false); setDrawer(true); }}>☰</button><div><span className="topbar-kicker">{idText("NADI / RELIABILITY PLATFORM")}</span><span className="topbar-title">PLTU Banten 1 Suralaya</span></div></div><div className="topbar-actions"><span className="topbar-status">{idText("Mart read-only")} <span className="scope-chip">BSR / IP</span></span><ThemeToggle /><WorkspaceAccount /></div></header>
      <main id="main-content" tabIndex={-1} className="nadi-main">{children}</main>
    </div>
  </div>;
}

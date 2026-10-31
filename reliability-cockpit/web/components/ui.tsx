"use client";

import { idText, statusLabel } from "../lib/id-copy";
import Link from "next/link";
import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, useId } from "react";
import type { PageMeta } from "../lib/api";
import { shortIdentifier } from "../lib/format";

export { AppShell } from "./AppNavigation";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <div className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</div>;
}

export function StatCard({ label, value, detail, tone = "default" }: { label: string; value: string | number; detail: string; tone?: "default" | "accent" | "muted" }) {
  return <article className={`stat-card ${tone}`}><span>{label}</span><strong className={typeof value === "string" && !/^[\d.,]+$/.test(value) ? "stat-text-value" : undefined}>{typeof value === 'string' ? statusLabel(value) : value}</strong><small>{detail}</small></article>;
}

export function DataMaturity({ state, detail }: { state: string; detail?: string }) {
  return <span className="maturity-badge" title={detail}>{statusLabel(state)}</span>;
}

export type StatusBadgeMode = "semantic" | "raw-neutral";

export function StatusBadge({ value, mode = "raw-neutral" }: { value: string | null | undefined; mode?: StatusBadgeMode }) {
  const normalized = value?.toUpperCase() ?? "UNKNOWN";
  const tone = mode === "semantic" && (normalized.includes("CLOSE") || normalized.includes("COMPLETE") || normalized === "ACTIVE" || normalized === "OPERATING") ? "positive" : "neutral";
  return <span className={`status-badge ${tone}`} title={value ?? undefined}>{statusLabel(value ?? statusLabel("UNKNOWN"))}</span>;
}

export function Identifier({ value }: { value: string | null | undefined }) {
  return <span className="identifier" title={value ?? undefined}>{shortIdentifier(value)}</span>;
}

export function LoadingState({ label = "Memuat data Reliability Mart…" }: { label?: string }) {
  return <div className="state-card loading-state" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />{label}</div>;
}

export function EmptyState({ title = "Belum ada data Reliability Mart untuk tampilan ini.", detail }: { title?: string; detail?: string }) {
  return <div className="state-card empty-state"><span className="state-symbol" aria-hidden="true">∅</span><strong>{title}</strong>{detail && <p>{detail}</p>}</div>;
}

export function ErrorState({ message = idText("Reliability Mart unavailable"), onRetry, variant = "service" }: { message?: string; onRetry?: () => void; variant?: "service" | "access" | "session" | "request" }) {
  const detail = variant === "access" ? "Akun ini belum memiliki capability atau scope portofolio faktual yang disetujui. Hubungi operator berwenang untuk verifikasi akses; status ini tidak menyatakan Reliability Mart mengalami gangguan." : variant === "session" ? "Masuk kembali melalui halaman login untuk memperbarui sesi." : variant === "request" ? "Permintaan tidak dapat diproses. Periksa konteks permintaan atau hubungi operator." : "Data Reliability Mart belum dapat dibaca. Coba muat ulang beberapa saat lagi.";
  return <div className="state-card error-state" role="alert"><span className="state-symbol" aria-hidden="true">!</span><strong>{message}</strong><p>{detail}</p>{variant === "session" && <Link className="button secondary" href="/login?returnTo=%2F">Masuk kembali</Link>}{variant === "service" && onRetry && <Button onClick={onRetry}>{idText("Try again")}</Button>}</div>;
}

export function Pagination({ meta, onChange }: { meta: PageMeta; onChange: (offset: number) => void }) {
  const first = meta.total === 0 ? 0 : meta.offset + 1;
  const last = Math.min(meta.offset + meta.limit, meta.total);
  return <div className="pagination"><span>{first}–{last} dari {meta.total.toLocaleString("id-ID")}</span><div><button className="icon-button" type="button" aria-label={idText("Previous page")} disabled={meta.offset === 0} onClick={() => onChange(Math.max(0, meta.offset - meta.limit))}>←</button><span className="page-number" aria-live="polite">{Math.floor(meta.offset / meta.limit) + 1}</span><button className="icon-button" type="button" aria-label={idText("Next page")} disabled={!meta.has_more} onClick={() => onChange(meta.offset + meta.limit)}>→</button></div></div>;
}

export function TableFrame({ children, minWidth = 900, label = idText("Data table, scroll horizontally for additional columns") }: { children: ReactNode; minWidth?: number; label?: string }) {
  return <div className="table-frame" role="region" aria-label={label} tabIndex={0}><div className="table-content" style={{ minWidth }}>{children}</div></div>;
}

export function SectionCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`section-card ${className}`}>{children}</section>;
}

export function Button({ variant = "secondary", className = "", type = "button", busy = false, disabled, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "tertiary" | "outline" | "ghost" | "destructive"; busy?: boolean }) {
  return <button {...props} type={type} disabled={disabled || busy} aria-busy={busy || props['aria-busy']} className={`button ${variant} ${className}`}>{busy && <span className="spinner" aria-hidden="true" />}{children}</button>;
}

/** Keep guidance reachable without competing with the engineer's current task. */
export function HelpDetails({ title, children }: { title: string; children: ReactNode }) {
  return <details className="help-details"><summary>{title}</summary><div>{children}</div></details>;
}

export function SearchField({ label, id, className = "", ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const generated = useId();
  const inputId = id ?? generated;
  return <label className="search-field" htmlFor={inputId}><span>{label}</span><span className="search-control"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input {...props} type="search" id={inputId} className={className}/></span></label>;
}

export function InputControl({ label, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; id: string }) {
  return <label htmlFor={id}>{label}<input {...props} id={id} className="input-control" /></label>;
}

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return <nav aria-label={idText("Breadcrumb")}><ol className="breadcrumbs">{items.map((item, index) => <li key={`${item.label}-${index}`}>{item.href ? <Link href={item.href}>{item.label}</Link> : <span aria-current={index === items.length - 1 ? "page" : undefined}>{item.label}</span>}</li>)}</ol></nav>;
}

export function Feedback({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={`feedback ${error ? "error" : ""}`} role={error ? "alert" : "status"}>{children}</div>;
}

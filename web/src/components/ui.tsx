import { type ReactNode, useState } from "react";

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="block"><span className="label">{label}</span>{children}{hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}</label>;
}
export function Alert({ kind = "error", children }: { kind?: "error" | "ok" | "info"; children: ReactNode }) {
  if (!children) return null;
  const c = { error: "bg-red-50 text-red-800 ring-red-200", ok: "bg-emerald-50 text-emerald-800 ring-emerald-200", info: "bg-sky-50 text-sky-900 ring-sky-200" }[kind];
  return <div role={kind === "error" ? "alert" : "status"} className={`rounded-xl px-4 py-3 text-sm ring-1 ${c}`}>{children}</div>;
}
export function Loading() { return <div className="p-6 text-center text-slate-500">Carregando…</div>; }
export function PageTitle({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return <div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-2xl font-bold">{title}</h1>{sub && <p className="text-sm text-slate-500">{sub}</p>}</div>{action}</div>;
}
/** Botão que executa uma ação assíncrona e mostra estado/erro. */
export function ActionButton({ onClick, children, className = "btn-primary", confirm }: { onClick: () => Promise<unknown>; children: ReactNode; className?: string; confirm?: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  return <span className="inline-flex flex-col">
    <button type="button" className={className} disabled={busy} onClick={async () => {
      if (confirm && !window.confirm(confirm)) return;
      setBusy(true); setErr("");
      try { await onClick(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
    }}>{busy ? "…" : children}</button>
    {err && <span className="mt-1 text-xs text-red-600">{err}</span>}
  </span>;
}
export const STATUS_LABEL: Record<string, string> = { NEW: "Novo", LEAD: "Potencial cliente", QUALIFIED: "Qualificado", CUSTOMER: "Cliente", LOST: "Perdido", BOT: "IA atendendo", HUMAN: "Aguardando humano", CLOSED: "Encerrada" };
export const CHANNEL_LABEL: Record<string, string> = { WIDGET: "Site", WHATSAPP: "WhatsApp", TELEGRAM: "Telegram" };

import { useState } from "react";
import { api, dt } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, CHANNEL_LABEL, Field, Loading, PageTitle, STATUS_LABEL } from "../components/ui";

export function Contacts() {
  const [q, setQ] = useState(""); const [tab, setTab] = useState<"contacts" | "quotes">("contacts");
  const list = useAsync(() => api<any[]>(`/contacts?q=${encodeURIComponent(q)}`), [q]);
  const quotes = useAsync(() => api<any[]>("/quotes"), []);
  const [edit, setEdit] = useState<any | null>(null);
  return <div>
    <PageTitle title="CRM" sub="Clientes, potenciais clientes e pedidos de orçamento" action={<a className="btn-ghost" href="/api/contacts.csv" download>⬇ Exportar CSV</a>} />
    <div className="mb-3 flex gap-2">{(["contacts", "quotes"] as const).map((t) => <button key={t} onClick={() => setTab(t)} className={`badge px-3 py-2 ${tab === t ? "bg-brand-600 text-white" : "bg-white ring-1 ring-slate-200"}`}>{t === "contacts" ? "Contatos" : "Orçamentos"}</button>)}</div>
    {tab === "contacts" ? <>
      <input className="input mb-3" placeholder="Buscar por nome, telefone ou e-mail" value={q} onChange={(e) => setQ(e.target.value)} />
      {list.error && <Alert>{list.error}</Alert>}
      {!list.data ? <Loading /> : <div className="space-y-2">
        {list.data.length === 0 && <p className="card text-center text-slate-500">Nenhum contato.</p>}
        {list.data.map((c) => <button key={c.id} onClick={() => setEdit(c)} className="card block w-full text-left hover:ring-brand-500">
          <div className="flex flex-wrap items-center justify-between gap-2"><b>{c.name || "Sem nome"}</b><span className="badge bg-brand-50 text-brand-700">{STATUS_LABEL[c.status]}</span></div>
          <p className="text-sm text-slate-500">{[c.phone, c.email, CHANNEL_LABEL[c.channel], c.serviceInterest].filter(Boolean).join(" · ")}</p>
          <p className="text-xs text-slate-400">{c._count.conversations} conversa(s) · {c._count.bookings} agendamento(s) · {c._count.quotes} orçamento(s) · consentimento comercial: {c.marketingConsent ? "sim" : "não"}</p>
        </button>)}
      </div>}
    </> : <Quotes q={quotes} />}
    {edit && <ContactEditor c={edit} onClose={() => { setEdit(null); list.reload(); }} />}
  </div>;
}

function Quotes({ q }: { q: ReturnType<typeof useAsync<any[]>> }) {
  if (!q.data) return <Loading />;
  return <div className="space-y-2">
    {q.data.length === 0 && <p className="card text-center text-slate-500">Nenhum pedido de orçamento.</p>}
    {q.data.map((x) => <div key={x.id} className="card">
      <div className="flex flex-wrap justify-between gap-2"><b>{x.serviceName}</b><select className="rounded-lg border px-2 py-1 text-sm" value={x.status} onChange={async (e) => { await api(`/quotes/${x.id}`, { method: "PATCH", body: { status: e.target.value } }); q.reload(); }}>
        {[["open", "Aberto"], ["sent", "Enviado"], ["won", "Ganho"], ["lost", "Perdido"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
      <p className="mt-1 whitespace-pre-wrap text-sm">{x.details}</p>
      <p className="mt-1 text-xs text-slate-500">{x.contact.name || "Cliente"} {x.contact.phone} {x.contact.email} · {dt(x.createdAt)}</p>
    </div>)}
  </div>;
}

function ContactEditor({ c, onClose }: { c: any; onClose: () => void }) {
  const [f, setF] = useState({ name: c.name, phone: c.phone, email: c.email, serviceInterest: c.serviceInterest, status: c.status, notes: c.notes, marketingConsent: c.marketingConsent });
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
    <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-white p-5 sm:rounded-3xl" onClick={(e) => e.stopPropagation()}>
      <h2 className="mb-3 text-lg font-bold">Contato</h2>
      <div className="space-y-3">
        <Field label="Nome"><input className="input" value={f.name} onChange={set("name")} /></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Telefone"><input className="input" value={f.phone} onChange={set("phone")} /></Field><Field label="E-mail"><input className="input" value={f.email} onChange={set("email")} /></Field></div>
        <Field label="Serviço de interesse"><input className="input" value={f.serviceInterest} onChange={set("serviceInterest")} /></Field>
        <Field label="Status comercial"><select className="input" value={f.status} onChange={set("status")}>{["NEW", "LEAD", "QUALIFIED", "CUSTOMER", "LOST"].map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</select></Field>
        <Field label="Notas"><textarea className="input" rows={3} value={f.notes} onChange={set("notes")} /></Field>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1 h-5 w-5" checked={f.marketingConsent} onChange={set("marketingConsent")} /><span>O cliente consentiu explicitamente em receber mensagens comerciais{c.consentAt ? ` (registrado em ${dt(c.consentAt)})` : ""}. Só faça acompanhamento comercial com este consentimento.</span></label>
        <div className="flex flex-wrap gap-2 pt-2">
          <ActionButton onClick={async () => { await api(`/contacts/${c.id}`, { method: "PATCH", body: f }); onClose(); }}>Salvar</ActionButton>
          <a className="btn-ghost" href={`/api/contacts/${c.id}/export`} download>Exportar dados (RGPD)</a>
          <ActionButton className="btn-danger" confirm="Apagar definitivamente este contato e todo o histórico?" onClick={async () => { await api(`/contacts/${c.id}`, { method: "DELETE" }); onClose(); }}>Apagar</ActionButton>
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  </div>;
}

export function Calendar() {
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const to = new Date(month.getFullYear(), month.getMonth() + 1, 0, 23, 59);
  const list = useAsync(() => api<any[]>(`/bookings?from=${month.toISOString()}&to=${to.toISOString()}`), [month.getTime()]);
  const [sel, setSel] = useState<number>(new Date().getDate());
  const days = to.getDate(), offset = (month.getDay() + 6) % 7;
  const byDay = new Map<number, any[]>();
  list.data?.forEach((b) => { const d = new Date(b.startsAt).getDate(); byDay.set(d, [...(byDay.get(d) ?? []), b]); });
  return <div>
    <PageTitle title="Agenda" sub="Reservas criadas pelo agente" />
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <button className="btn-ghost px-3" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>‹</button>
        <b className="capitalize">{month.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</b>
        <button className="btn-ghost px-3" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>›</button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-slate-500">{["S", "T", "Q", "Q", "S", "S", "D"].map((d, i) => <div key={i}>{d}</div>)}</div>
      <div className="mt-1 grid grid-cols-7 gap-1">
        {Array.from({ length: offset }).map((_, i) => <div key={`e${i}`} />)}
        {Array.from({ length: days }, (_, i) => i + 1).map((d) => {
          const n = byDay.get(d)?.filter((b) => b.status === "CONFIRMED").length ?? 0;
          return <button key={d} onClick={() => setSel(d)} className={`aspect-square rounded-xl text-sm ${sel === d ? "bg-brand-600 text-white" : "bg-slate-50"}`}>{d}{n > 0 && <span className={`block text-[10px] font-bold ${sel === d ? "" : "text-brand-600"}`}>●{n}</span>}</button>;
        })}
      </div>
    </div>
    <div className="mt-3 space-y-2">
      {(byDay.get(sel) ?? []).length === 0 && <p className="card text-center text-slate-500">Sem reservas neste dia.</p>}
      {(byDay.get(sel) ?? []).map((b) => <div key={b.id} className={`card flex flex-wrap items-center justify-between gap-2 ${b.status === "CANCELLED" ? "opacity-50" : ""}`}>
        <div><b>{new Date(b.startsAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })} — {b.serviceName}</b><p className="text-sm text-slate-500">{b.contact.name || "Cliente"} {b.contact.phone} · {CHANNEL_LABEL[b.contact.channel]} {b.status === "CANCELLED" && "· cancelada"}</p></div>
        {b.status === "CONFIRMED" && <ActionButton className="btn-ghost text-sm" confirm="Cancelar esta reserva?" onClick={async () => { await api(`/bookings/${b.id}/cancel`, { method: "POST" }); list.reload(); }}>Cancelar</ActionButton>}
      </div>)}
    </div>
  </div>;
}

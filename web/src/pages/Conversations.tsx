import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, dt } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, CHANNEL_LABEL, Loading, PageTitle, STATUS_LABEL } from "../components/ui";
import { useApp } from "../components/AppLayout";

const STATUS_COLOR: Record<string, string> = { BOT: "bg-emerald-100 text-emerald-800", HUMAN: "bg-amber-100 text-amber-800", CLOSED: "bg-slate-100 text-slate-600" };

export function Conversations() {
  const [filter, setFilter] = useState("");
  const { onEvent } = useApp();
  const list = useAsync(() => api<any[]>(`/conversations${filter ? `?status=${filter}` : ""}`), [filter]);
  useEffect(() => onEvent(() => { list.reload(); }), [onEvent, list.reload]);
  return <div>
    <PageTitle title="Conversas" sub="Histórico de atendimento em todos os canais" />
    <div className="mb-3 flex gap-2 overflow-x-auto">
      {[["", "Todas"], ["HUMAN", "Aguardando humano"], ["BOT", "IA atendendo"], ["CLOSED", "Encerradas"]].map(([v, l]) =>
        <button key={v} onClick={() => setFilter(v)} className={`badge whitespace-nowrap px-3 py-2 ${filter === v ? "bg-brand-600 text-white" : "bg-white ring-1 ring-slate-200"}`}>{l}</button>)}
    </div>
    {list.error && <Alert>{list.error}</Alert>}
    {list.loading && !list.data ? <Loading /> : (
      <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">
        {list.data?.length === 0 && <li className="p-6 text-center text-slate-500">Nenhuma conversa ainda. Conecte um canal para começar.</li>}
        {list.data?.map((c) => <li key={c.id}><Link to={`/app/conversations/${c.id}`} className="flex items-center gap-3 p-4 hover:bg-slate-50">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-50 font-bold text-brand-700">{(c.contact.name || "?")[0].toUpperCase()}</div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2"><b className="truncate">{c.contact.name || c.contact.phone || "Visitante"}</b><span className="text-xs text-slate-400">{CHANNEL_LABEL[c.channel]}</span></div>
            <p className="truncate text-sm text-slate-500">{c.messages[0]?.content}</p>
          </div>
          <div className="text-right"><span className={`badge ${STATUS_COLOR[c.status]}`}>{STATUS_LABEL[c.status]}</span><p className="mt-1 text-xs text-slate-400">{dt(c.lastMessageAt)}</p></div>
        </Link></li>)}
      </ul>)}
  </div>;
}

export function ConversationDetail() {
  const { id } = useParams();
  const { onEvent } = useApp();
  const conv = useAsync(() => api(`/conversations/${id}`), [id]);
  const [text, setText] = useState(""); const [err, setErr] = useState(""); const [sending, setSending] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => onEvent((e) => { if (e.conversationId === id) conv.reload(); }), [onEvent, id, conv.reload]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [conv.data?.messages?.length]);
  if (conv.error) return <Alert>{conv.error}</Alert>;
  const c = conv.data; if (!c) return <Loading />;
  const setStatus = async (status: string) => { await api(`/conversations/${id}/status`, { body: { status } }); conv.reload(); };
  const send = async (e: React.FormEvent) => {
    e.preventDefault(); if (!text.trim()) return; setSending(true); setErr("");
    try { await api(`/conversations/${id}/reply`, { body: { text } }); setText(""); conv.reload(); } catch (x: any) { setErr(x.message); conv.reload(); } finally { setSending(false); }
  };
  return <div className="flex h-[calc(100vh-7rem)] flex-col lg:h-[calc(100vh-3rem)]">
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <Link to="/app/conversations" className="btn-ghost px-3">←</Link>
      <div className="min-w-0 flex-1"><b>{c.contact.name || "Visitante"}</b><p className="text-xs text-slate-500">{CHANNEL_LABEL[c.channel]} · {c.contact.phone || c.contact.email || c.contact.externalId.slice(0, 12)} · {STATUS_LABEL[c.status]}</p></div>
      {c.status !== "HUMAN" && <ActionButton className="btn-ghost text-sm" onClick={() => setStatus("HUMAN")}>Assumir atendimento</ActionButton>}
      {c.status === "HUMAN" && <ActionButton className="btn-ghost text-sm" onClick={() => setStatus("BOT")}>Devolver para IA</ActionButton>}
      {c.status !== "CLOSED" && <ActionButton className="btn-ghost text-sm" onClick={() => setStatus("CLOSED")}>Encerrar</ActionButton>}
    </div>
    <div className="flex-1 space-y-2 overflow-y-auto rounded-2xl bg-slate-100 p-3">
      {c.messages.map((m: any) => <div key={m.id} className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${m.role === "customer" ? "bg-white" : m.role === "human" ? "ml-auto bg-amber-500 text-white" : "ml-auto bg-brand-600 text-white"}`}>
        <p className="whitespace-pre-wrap break-words">{m.content}</p><p className="mt-1 text-[10px] opacity-70">{m.role === "assistant" ? "IA" : m.role === "human" ? "Você" : "Cliente"} · {dt(m.createdAt)}</p>
      </div>)}
      <div ref={end} />
    </div>
    {err && <div className="mt-2"><Alert>{err}</Alert></div>}
    <form onSubmit={send} className="mt-3 flex gap-2">
      <input className="input" placeholder="Responder como atendente…" value={text} onChange={(e) => setText(e.target.value)} maxLength={4000} />
      <button className="btn-primary" disabled={sending}>Enviar</button>
    </form>
    <p className="mt-1 text-xs text-slate-500">Ao responder, a IA é pausada nesta conversa até você devolvê-la.{c.channel === "WHATSAPP" && " WhatsApp: mensagens livres só são entregues até 24h após a última mensagem do cliente."}</p>
  </div>;
}

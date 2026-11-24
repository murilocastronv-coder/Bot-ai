import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { Alert, Loading, PageTitle } from "../components/ui";
import { useApp } from "../components/AppLayout";
import { useEffect } from "react";

export default function Dashboard() {
  const { me, onEvent } = useApp();
  const stats = useAsync(() => api("/stats"));
  const biz = useAsync(() => api("/business"));
  useEffect(() => onEvent(() => { stats.reload(); }), [onEvent, stats.reload]);
  if (stats.loading && !stats.data) return <Loading />;
  if (stats.error || biz.error) return <Alert>{stats.error || biz.error}</Alert>;
  const s = stats.data, b = biz.data;
  if (!s || !b) return <Loading />;
  const quota = b.planDef.aiResponses, used = b.aiUsedThisMonth, pct = Math.min(100, Math.round((used / quota) * 100));
  const toggle = async () => { await api("/business/agent", { body: { enabled: !b.agentEnabled } }); biz.reload(); };
  const trialDays = Math.ceil((new Date(b.trialEndsAt).getTime() - Date.now()) / 86400000);

  return <div className="space-y-4">
    <PageTitle title={`Olá, ${me?.name?.split(" ")[0] ?? ""}`} sub={b.name} />
    {!b.planActive && <Alert>{b.plan === "FREE" ? "Seu teste gratuito terminou." : "Sua assinatura não está ativa."} O agente responde apenas com uma mensagem padrão. <Link className="font-semibold underline" to="/app/billing">Escolher um plano</Link></Alert>}
    {b.plan === "FREE" && b.planActive && <Alert kind="info">Teste gratuito: {trialDays} dia(s) restante(s).</Alert>}

    <div className="card flex flex-wrap items-center justify-between gap-4">
      <div><p className="text-sm text-slate-500">Agente de IA</p><p className="text-lg font-bold">{b.agentEnabled ? "🟢 Ativo — respondendo clientes" : "⚪ Desativado"}</p></div>
      <button type="button" role="switch" aria-checked={b.agentEnabled} onClick={toggle} className={`relative h-9 w-16 rounded-full transition ${b.agentEnabled ? "bg-emerald-500" : "bg-slate-300"}`}>
        <span className={`absolute top-1 h-7 w-7 rounded-full bg-white shadow transition ${b.agentEnabled ? "left-8" : "left-1"}`} />
      </button>
    </div>

    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {[["Mensagens recebidas", s.messagesReceived], ["Clientes atendidos", s.contactsServed], ["Novos potenciais clientes", s.newLeads], ["Agendamentos", s.bookings],
        ["Conversas em andamento", s.openConversations], ["Aguardando humano", s.waitingHuman], ["Taxa de conversão", `${s.conversionRate}%`], ["Custo IA (estimado)", `$${s.ai.costUsd.toFixed(2)}`]]
        .map(([l, v]) => <div key={l as string} className="card"><p className="text-xs text-slate-500">{l}</p><p className="mt-1 text-2xl font-bold">{v}</p></div>)}
    </div>
    <div className="card">
      <div className="flex justify-between text-sm"><span>Respostas de IA este mês ({b.planDef.name})</span><span className="font-semibold">{used} / {quota}</span></div>
      <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100"><div className={`h-full ${pct > 90 ? "bg-red-500" : "bg-brand-600"}`} style={{ width: `${pct}%` }} /></div>
      <p className="mt-2 text-xs text-slate-500">Mês {s.month}. Tokens: {s.ai.promptTokens + s.ai.completionTokens}. Ao atingir o limite, as conversas passam para atendimento humano.</p>
    </div>
    <div className="grid gap-3 sm:grid-cols-3">
      <Link to="/app/agent" className="card hover:ring-brand-500">🤖 <b>Configurar agente</b><p className="text-sm text-slate-500">Serviços, preços, horários, FAQ</p></Link>
      <Link to="/app/channels" className="card hover:ring-brand-500">🔌 <b>Conectar canais</b><p className="text-sm text-slate-500">Site, WhatsApp, Telegram</p></Link>
      <Link to="/app/conversations" className="card hover:ring-brand-500">💬 <b>Ver conversas</b><p className="text-sm text-slate-500">Assuma o atendimento</p></Link>
    </div>
  </div>;
}

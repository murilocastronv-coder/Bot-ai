import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, Loading, PageTitle } from "../components/ui";

const STATUS: Record<string, string> = { trialing: "Em teste", active: "Ativa", past_due: "Pagamento pendente", canceled: "Cancelada", unpaid: "Não paga", incomplete: "Incompleta" };

export default function Billing() {
  const [q] = useSearchParams();
  const biz = useAsync(() => api("/business"));
  const plans = useAsync(() => api<any[]>("/billing/plans"));
  if (!biz.data || !plans.data) return <Loading />;
  const b = biz.data;
  const go = async (path: string, body?: object) => { const r = await api(path, { method: "POST", body }); window.location.href = r.url; };
  return <div className="space-y-4">
    <PageTitle title="Assinatura" />
    {q.get("status") === "success" && <Alert kind="ok">Pagamento recebido! A ativação do plano é confirmada pela Stripe em alguns segundos — atualize a página.</Alert>}
    {q.get("status") === "cancel" && <Alert kind="info">Pagamento cancelado. Nenhuma cobrança foi feita.</Alert>}
    <div className="card">
      <p className="text-sm text-slate-500">Plano atual</p>
      <p className="text-2xl font-bold">{b.planDef.name} <span className="text-base font-normal text-slate-500">· {STATUS[b.subscriptionStatus] ?? b.subscriptionStatus}</span></p>
      {b.plan === "FREE" && <p className="text-sm">Teste gratuito até {new Date(b.trialEndsAt).toLocaleDateString("pt-BR")}.</p>}
      {b.currentPeriodEnd && <p className="text-sm">Renovação automática em {new Date(b.currentPeriodEnd).toLocaleDateString("pt-BR")}.</p>}
      {b.stripeCustomerId && <div className="mt-3"><ActionButton className="btn-ghost" onClick={() => go("/billing/portal")}>Gerenciar assinatura, faturas e cancelamento</ActionButton></div>}
    </div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {plans.data.map((p) => <div key={p.id} className={`card flex flex-col ${p.id === b.plan ? "ring-2 ring-brand-600" : ""}`}>
        <b>{p.name}</b><p className="text-2xl font-extrabold">{p.priceEur.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}<span className="text-sm font-normal">/mês</span></p>
        <ul className="mt-2 flex-1 space-y-1 text-sm"><li>{p.aiResponses} respostas de IA</li><li>Canais: {p.channels.map((c: string) => ({ WIDGET: "Site", WHATSAPP: "WhatsApp", TELEGRAM: "Telegram" } as any)[c]).join(", ")}</li><li>CRM {p.crm === "full" ? "completo" : "básico"}</li>{p.booking && <li>Agendamento automático</li>}<li>Até {p.maxUsers} usuário(s)</li></ul>
        {p.id !== "FREE" && p.id !== b.plan && (b.stripeSubscriptionId
          ? <ActionButton className="btn-ghost mt-3" onClick={() => go("/billing/portal")}>Trocar de plano</ActionButton>
          : <ActionButton className="btn-primary mt-3" onClick={() => go("/billing/checkout", { plan: p.id })}>Assinar</ActionButton>)}
        {p.id === b.plan && <span className="mt-3 text-center text-sm font-semibold text-brand-700">Plano atual</span>}
      </div>)}
    </div>
    <p className="text-xs text-slate-500">Pagamentos processados pela Stripe. Cupons promocionais podem ser informados na página de pagamento.</p>
  </div>;
}

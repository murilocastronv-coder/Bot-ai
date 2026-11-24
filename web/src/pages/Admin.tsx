import { useState } from "react";
import { api, dt } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, Field, Loading, PageTitle } from "../components/ui";

export default function Admin() {
  const stats = useAsync(() => api("/admin/stats"));
  const list = useAsync(() => api<any[]>("/admin/businesses"));
  const errors = useAsync(() => api<any[]>("/admin/errors"));
  const revenue = useAsync(() => api("/admin/revenue").catch(() => null));
  const [coupon, setCoupon] = useState({ code: "", percentOff: 20, durationMonths: 3 }); const [ok, setOk] = useState("");
  if (stats.error) return <Alert>{stats.error}</Alert>;
  const s = stats.data; if (!s) return <Loading />;
  return <div className="space-y-4">
    <PageTitle title="Administração geral" />
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {[["Empresas", s.businesses], ["Assinaturas ativas", s.activeSubscriptions], ["MRR", `${s.mrrEur.toFixed(2)} €`], ["Faturado no mês (Stripe)", revenue.data ? `${revenue.data.paidEur.toFixed(2)} €` : "—"],
        ["Respostas IA (mês)", s.aiResponsesMonth], ["Custo IA (mês, estimado)", `$${s.aiCostUsdMonth.toFixed(2)}`], ["Erros 24h", s.errors24h], ["Servidor", `${s.server.rssMb} MB · DB ${s.server.dbLatencyMs} ms · up ${Math.round(s.server.uptimeSec / 3600)} h`]]
        .map(([l, v]) => <div key={l as string} className="card"><p className="text-xs text-slate-500">{l}</p><p className="mt-1 text-lg font-bold">{v}</p></div>)}
    </div>
    <div className="card overflow-x-auto"><h2 className="mb-2 font-semibold">Empresas e consumo</h2>
      <table className="w-full min-w-[640px] text-left text-sm"><thead className="text-slate-500"><tr><th>Empresa</th><th>Plano</th><th>Status</th><th>IA mês</th><th>Custo</th><th></th></tr></thead>
        <tbody>{list.data?.map((b) => <tr key={b.id} className="border-t border-slate-100">
          <td className="py-2"><b>{b.name}</b><br /><span className="text-xs text-slate-500">{b.users[0]?.email}</span></td><td>{b.plan}</td><td>{b.blocked ? "🚫 bloqueada" : b.subscriptionStatus}</td><td>{b.aiResponsesMonth}</td><td>${b.aiCostUsdMonth.toFixed(3)}</td>
          <td className="flex gap-1 py-2"><ActionButton className="btn-ghost text-xs" confirm={b.blocked ? "Desbloquear?" : "Bloquear esta conta?"} onClick={async () => { await api(`/admin/businesses/${b.id}/block`, { body: { blocked: !b.blocked } }); list.reload(); }}>{b.blocked ? "Desbloquear" : "Bloquear"}</ActionButton>
            <select className="rounded border text-xs" value={b.plan} onChange={async (e) => { await api(`/admin/businesses/${b.id}/plan`, { body: { plan: e.target.value } }); list.reload(); }}>{["FREE", "STARTER", "PROFESSIONAL", "BUSINESS"].map((p) => <option key={p}>{p}</option>)}</select></td>
        </tr>)}</tbody></table></div>
    <div className="card space-y-3"><h2 className="font-semibold">Criar cupom promocional (Stripe)</h2><Alert kind="ok">{ok}</Alert>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Código"><input className="input uppercase" value={coupon.code} onChange={(e) => setCoupon({ ...coupon, code: e.target.value.toUpperCase() })} /></Field>
        <Field label="% de desconto"><input className="input" type="number" min={1} max={100} value={coupon.percentOff} onChange={(e) => setCoupon({ ...coupon, percentOff: Number(e.target.value) })} /></Field>
        <Field label="Duração (meses)"><input className="input" type="number" min={1} max={24} value={coupon.durationMonths} onChange={(e) => setCoupon({ ...coupon, durationMonths: Number(e.target.value) })} /></Field>
      </div>
      <ActionButton onClick={async () => { const r = await api("/admin/coupons", { body: coupon }); setOk(`Cupom ${r.code} criado.`); }}>Criar cupom</ActionButton></div>
    <div className="card"><h2 className="mb-2 font-semibold">Logs de erros</h2>
      <ul className="max-h-96 space-y-1 overflow-y-auto font-mono text-xs">{errors.data?.map((e) => <li key={e.id} className="border-b border-slate-100 py-1"><span className="text-slate-400">{dt(e.createdAt)}</span> <b>{e.source}</b> {e.message}</li>)}</ul></div>
  </div>;
}

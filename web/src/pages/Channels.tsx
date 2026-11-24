import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, Field, Loading, PageTitle } from "../components/ui";

export default function Channels() {
  const biz = useAsync(() => api("/business"));
  const [tg, setTg] = useState(""); const [wa, setWa] = useState({ phoneNumberId: "", accessToken: "" });
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState(false);
  if (biz.error) return <Alert>{biz.error}</Alert>;
  const b = biz.data; if (!b) return <Loading />;
  const snippet = `<script src="${location.origin}/widget.js" data-key="${b.widgetKey}" async></script>`;
  const can = (c: string) => b.planDef.channels.includes(c);
  const upgrade = <Link to="/app/billing" className="font-semibold text-brand-600 underline">Ver planos</Link>;

  return <div className="space-y-4">
    <PageTitle title="Canais" sub="Onde o seu agente atende os clientes" />
    <Alert kind="ok">{msg}</Alert>

    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">🌐 Chat no seu site</h2>
      <p className="text-sm text-slate-600">Cole este código antes de <code>&lt;/body&gt;</code> no seu site (WordPress, Wix, Shopify: use a opção “código personalizado / HTML”).</p>
      <pre className="overflow-x-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100">{snippet}</pre>
      <button className="btn-ghost" onClick={async () => { try { await navigator.clipboard.writeText(snippet); setCopied(true); } catch { setCopied(false); } }}>{copied ? "Copiado ✓" : "Copiar código"}</button>
    </section>

    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">✈️ Telegram</h2>
      {b.telegramConnected ? <>
        <Alert kind="ok">Conectado ao bot <a className="font-semibold underline" href={`https://t.me/${b.telegramBotUsername}`} target="_blank" rel="noreferrer">@{b.telegramBotUsername}</a>. Os clientes já podem conversar com ele.</Alert>
        <ActionButton className="btn-ghost" confirm="Desconectar o bot do Telegram?" onClick={async () => { await api("/channels/telegram", { method: "DELETE" }); biz.reload(); }}>Desconectar</ActionButton>
      </> : !can("TELEGRAM") ? <p className="text-sm">Disponível nos planos Professional e Business. {upgrade}</p> : <>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>No Telegram, abra <a className="text-brand-600 underline" href="https://t.me/BotFather" target="_blank" rel="noreferrer">@BotFather</a> e envie <code>/newbot</code>.</li>
          <li>Escolha um nome e um usuário terminado em “bot”.</li>
          <li>Copie o token recebido (formato <code>123456:ABC…</code>) e cole abaixo.</li>
        </ol>
        <Field label="Token do bot"><input className="input font-mono" value={tg} onChange={(e) => setTg(e.target.value.trim())} placeholder="123456789:AA..." autoComplete="off" /></Field>
        <ActionButton onClick={async () => { const r = await api("/channels/telegram", { body: { token: tg } }); setTg(""); setMsg(`Bot @${r.username} conectado!`); biz.reload(); }}>Conectar Telegram</ActionButton>
      </>}
    </section>

    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">🟢 WhatsApp Business (API oficial da Meta)</h2>
      {b.whatsappConnected ? <>
        <Alert kind="ok">Número conectado (Phone Number ID {b.waPhoneNumberId}).</Alert>
        <ActionButton className="btn-ghost" confirm="Desconectar o WhatsApp?" onClick={async () => { await api("/channels/whatsapp", { method: "DELETE" }); biz.reload(); }}>Desconectar</ActionButton>
      </> : !can("WHATSAPP") ? <p className="text-sm">Disponível a partir do plano Starter. {upgrade}</p> : <>
        <details className="text-sm text-slate-600"><summary className="cursor-pointer font-medium text-slate-800">Como obter os dados (passo a passo)</summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>Tenha uma conta <b>Meta Business</b> verificada e um número de telefone que não esteja em uso no app WhatsApp.</li>
            <li>Em developers.facebook.com, o administrador da plataforma deve ter criado o app com o produto WhatsApp e assinado o webhook (veja a documentação).</li>
            <li>No WhatsApp Manager, adicione e verifique o número. Copie o <b>Phone Number ID</b>.</li>
            <li>Em Configurações do negócio → Usuários do sistema, gere um <b>token permanente</b> com as permissões <code>whatsapp_business_messaging</code> e <code>whatsapp_business_management</code>.</li>
          </ol></details>
        <Field label="Phone Number ID"><input className="input font-mono" inputMode="numeric" value={wa.phoneNumberId} onChange={(e) => setWa({ ...wa, phoneNumberId: e.target.value.trim() })} /></Field>
        <Field label="Token de acesso permanente"><input className="input font-mono" type="password" autoComplete="off" value={wa.accessToken} onChange={(e) => setWa({ ...wa, accessToken: e.target.value.trim() })} /></Field>
        <ActionButton onClick={async () => { const r = await api("/channels/whatsapp", { body: wa }); setWa({ phoneNumberId: "", accessToken: "" }); setMsg(`WhatsApp ${r.display_phone_number} (${r.verified_name}) conectado!`); biz.reload(); }}>Conectar WhatsApp</ActionButton>
      </>}
    </section>

    <section className="card text-sm text-slate-500">Instagram, Messenger e Google Calendar: em desenvolvimento — exigem aprovação de app (Meta App Review / Google OAuth verification) antes de serem oferecidos.</section>
  </div>;
}

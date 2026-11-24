import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { ActionButton, Field, PageTitle } from "../components/ui";
import { useApp } from "../components/AppLayout";

export default function Account() {
  const { me } = useApp(); const nav = useNavigate();
  const [pw, setPw] = useState("");
  return <div className="space-y-4">
    <PageTitle title="Conta" />
    <div className="card"><p><b>{me?.name}</b></p><p className="text-sm text-slate-500">{me?.email}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <ActionButton className="btn-ghost" onClick={async () => { await api("/auth/logout", { method: "POST" }); nav("/login"); }}>Sair</ActionButton>
        {"Notification" in window && Notification.permission !== "granted" && <ActionButton className="btn-ghost" onClick={() => Notification.requestPermission()}>Ativar notificações</ActionButton>}
      </div></div>
    <div className="card space-y-2"><h2 className="font-semibold">Meus dados (RGPD)</h2>
      <p className="text-sm text-slate-600">Baixe uma cópia completa dos dados da empresa, clientes, conversas e agendamentos.</p>
      <a className="btn-ghost" href="/api/account/export" download>⬇ Exportar dados (JSON)</a></div>
    <div className="card space-y-3 ring-red-200"><h2 className="font-semibold text-red-700">Excluir conta</h2>
      <p className="text-sm text-slate-600">Apaga definitivamente a empresa, usuários, contatos, conversas e cancela a assinatura. Não pode ser desfeito.</p>
      <Field label="Confirme sua senha"><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" /></Field>
      <ActionButton className="btn-danger" confirm="Tem certeza? Todos os dados serão apagados." onClick={async () => { await api("/account", { method: "DELETE", body: { password: pw } }); nav("/"); }}>Excluir minha conta</ActionButton></div>
  </div>;
}

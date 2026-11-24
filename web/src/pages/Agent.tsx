import { useEffect, useState } from "react";
import { api, eur, upload } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionButton, Alert, Field, Loading, PageTitle } from "../components/ui";

const DAYS = [["mon", "Segunda"], ["tue", "Terça"], ["wed", "Quarta"], ["thu", "Quinta"], ["fri", "Sexta"], ["sat", "Sábado"], ["sun", "Domingo"]] as const;
const LANGS = [["fr", "Francês"], ["pt", "Português"], ["en", "Inglês"], ["es", "Espanhol"]] as const;

export default function Agent() {
  const biz = useAsync(() => api("/business"));
  const templates = useAsync(() => api<any[]>("/templates"));
  const [tab, setTab] = useState<"info" | "services" | "faq" | "docs">("info");
  if (biz.error) return <Alert>{biz.error}</Alert>;
  if (!biz.data || !templates.data) return <Loading />;
  return <div>
    <PageTitle title="Configurar agente" sub="O agente usa somente estas informações para responder" />
    <div className="mb-4 flex gap-2 overflow-x-auto">
      {([["info", "Empresa"], ["services", "Serviços e preços"], ["faq", "Perguntas frequentes"], ["docs", "Documentos"]] as const).map(([k, l]) =>
        <button key={k} onClick={() => setTab(k)} className={`badge whitespace-nowrap px-3 py-2 ${tab === k ? "bg-brand-600 text-white" : "bg-white ring-1 ring-slate-200"}`}>{l}</button>)}
    </div>
    {tab === "info" && <Info b={biz.data} templates={templates.data} onSaved={biz.reload} />}
    {tab === "services" && <Services />}
    {tab === "faq" && <Faqs suggestions={biz.data.templateDef.suggestedFaqs} />}
    {tab === "docs" && <Docs />}
  </div>;
}

function Info({ b, templates, onSaved }: { b: any; templates: any[]; onSaved: () => void }) {
  const [f, setF] = useState({ name: b.name, template: b.template, address: b.address, phone: b.phone, personality: b.personality, customInstructions: b.customInstructions, languages: b.languages as string[], timezone: b.timezone, slotMinutes: b.slotMinutes, openingHours: b.openingHours ?? {} });
  const [ok, setOk] = useState(false);
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  const tpl = templates.find((t) => t.id === f.template);
  const setDay = (d: string, v: [string, string][] | undefined) => setF({ ...f, openingHours: { ...f.openingHours, [d]: v } });
  return <div className="card space-y-4">
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Nome da empresa"><input className="input" value={f.name} onChange={set("name")} /></Field>
      <Field label="Tipo de atividade"><select className="input" value={f.template} onChange={set("template")}>{templates.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}</select></Field>
      <Field label="Endereço"><input className="input" value={f.address} onChange={set("address")} /></Field>
      <Field label="Telefone"><input className="input" value={f.phone} onChange={set("phone")} /></Field>
    </div>
    {tpl && <Alert kind="info"><b>Fluxo do modelo “{tpl.label}”:</b> {tpl.flow}</Alert>}
    <div>
      <span className="label">Horários de funcionamento</span>
      <div className="space-y-2">{DAYS.map(([d, label]) => {
        const v: [string, string][] | undefined = f.openingHours[d];
        const open = !!v?.length;
        return <div key={d} className="flex flex-wrap items-center gap-2">
          <label className="flex w-28 items-center gap-2"><input type="checkbox" className="h-5 w-5" checked={open} onChange={(e) => setDay(d, e.target.checked ? [["09:00", "18:00"]] : undefined)} />{label}</label>
          {open ? v!.map((r, i) => <span key={i} className="flex items-center gap-1">
            <input type="time" className="input w-28 py-1.5" value={r[0]} onChange={(e) => setDay(d, v!.map((x, j) => j === i ? [e.target.value, x[1]] : x))} />–
            <input type="time" className="input w-28 py-1.5" value={r[1]} onChange={(e) => setDay(d, v!.map((x, j) => j === i ? [x[0], e.target.value] : x))} />
            {v!.length > 1 && <button className="px-2 text-red-600" onClick={() => setDay(d, v!.filter((_, j) => j !== i))}>×</button>}
          </span>) : <span className="text-sm text-slate-400">Fechado</span>}
          {open && v!.length < 3 && <button className="text-sm text-brand-600" onClick={() => setDay(d, [...v!, ["14:00", "18:00"]])}>+ intervalo</button>}
        </div>;
      })}</div>
    </div>
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Fuso horário"><input className="input" value={f.timezone} onChange={set("timezone")} placeholder="Europe/Paris" /></Field>
      <Field label="Intervalo entre horários de agendamento (min)"><input className="input" type="number" min={10} max={240} value={f.slotMinutes} onChange={(e) => setF({ ...f, slotMinutes: Number(e.target.value) })} /></Field>
    </div>
    <div><span className="label">Idiomas atendidos</span><div className="flex flex-wrap gap-3">{LANGS.map(([id, l]) =>
      <label key={id} className="flex items-center gap-2"><input type="checkbox" className="h-5 w-5" checked={f.languages.includes(id)} onChange={(e) => setF({ ...f, languages: e.target.checked ? [...f.languages, id] : f.languages.filter((x) => x !== id) })} />{l}</label>)}</div></div>
    <Field label="Personalidade do agente" hint="Ex.: simpático e descontraído, trata o cliente por 'você'."><input className="input" value={f.personality} onChange={set("personality")} maxLength={500} /></Field>
    <Field label="Instruções personalizadas" hint="Políticas, regras de cancelamento, formas de pagamento, o que o agente não deve fazer…"><textarea className="input" rows={5} value={f.customInstructions} onChange={set("customInstructions")} maxLength={4000} /></Field>
    {ok && <Alert kind="ok">Configuração salva. O agente já usa as novas informações.</Alert>}
    <ActionButton onClick={async () => { setOk(false); await api("/business", { method: "PUT", body: f }); setOk(true); onSaved(); }}>Salvar</ActionButton>
  </div>;
}

function Services() {
  const list = useAsync(() => api<any[]>("/services"));
  const empty = { name: "", description: "", price: "", priceNote: "", durationMin: 30, bookable: true };
  const [f, setF] = useState<any>(empty);
  const save = async () => {
    const price = f.price === "" ? null : Math.round(Number(String(f.price).replace(",", ".")) * 100);
    if (price !== null && Number.isNaN(price)) throw new Error("Preço inválido");
    await api("/services", { body: { name: f.name, description: f.description, priceCents: price, priceNote: f.priceNote, durationMin: Number(f.durationMin), bookable: f.bookable } });
    setF(empty); list.reload();
  };
  return <div className="space-y-3">
    <div className="card space-y-3">
      <h2 className="font-semibold">Adicionar serviço</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Nome"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Preço (€)" hint="Deixe vazio se o preço depende de orçamento — o agente não inventará valor."><input className="input" inputMode="decimal" value={f.price} onChange={(e) => setF({ ...f, price: e.target.value })} /></Field>
        <Field label="Observação de preço"><input className="input" placeholder="ex.: a partir de, por m²" value={f.priceNote} onChange={(e) => setF({ ...f, priceNote: e.target.value })} /></Field>
        <Field label="Duração (min)"><input className="input" type="number" min={5} value={f.durationMin} onChange={(e) => setF({ ...f, durationMin: e.target.value })} /></Field>
      </div>
      <Field label="Descrição"><textarea className="input" rows={2} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
      <label className="flex items-center gap-2"><input type="checkbox" className="h-5 w-5" checked={f.bookable} onChange={(e) => setF({ ...f, bookable: e.target.checked })} />Pode ser agendado pelo agente</label>
      <ActionButton onClick={save}>Adicionar</ActionButton>
    </div>
    {list.data?.map((s) => <div key={s.id} className="card flex items-start justify-between gap-3">
      <div><b>{s.name}</b> <span className="text-brand-700">{eur(s.priceCents)}</span> {s.priceNote && <span className="text-sm text-slate-500">({s.priceNote})</span>}
        <p className="text-sm text-slate-500">{s.durationMin} min{s.bookable ? " · agendável" : ""}{s.description ? ` · ${s.description}` : ""}</p></div>
      <ActionButton className="btn-ghost text-sm text-red-600" confirm="Remover este serviço?" onClick={async () => { await api(`/services/${s.id}`, { method: "DELETE" }); list.reload(); }}>Remover</ActionButton>
    </div>)}
  </div>;
}

function Faqs({ suggestions }: { suggestions: string[] }) {
  const list = useAsync(() => api<any[]>("/faqs"));
  const [f, setF] = useState({ question: "", answer: "" });
  return <div className="space-y-3">
    <div className="card space-y-3">
      <h2 className="font-semibold">Nova pergunta frequente</h2>
      {suggestions?.length > 0 && <div className="flex flex-wrap gap-2">{suggestions.map((s) => <button key={s} className="badge bg-brand-50 px-3 py-1.5 text-brand-700" onClick={() => setF({ ...f, question: s })}>{s}</button>)}</div>}
      <Field label="Pergunta"><input className="input" value={f.question} onChange={(e) => setF({ ...f, question: e.target.value })} /></Field>
      <Field label="Resposta"><textarea className="input" rows={3} value={f.answer} onChange={(e) => setF({ ...f, answer: e.target.value })} /></Field>
      <ActionButton onClick={async () => { await api("/faqs", { body: f }); setF({ question: "", answer: "" }); list.reload(); }}>Adicionar</ActionButton>
    </div>
    {list.data?.map((x) => <div key={x.id} className="card flex justify-between gap-3"><div><b>{x.question}</b><p className="text-sm text-slate-600">{x.answer}</p></div>
      <ActionButton className="btn-ghost text-sm text-red-600" onClick={async () => { await api(`/faqs/${x.id}`, { method: "DELETE" }); list.reload(); }}>Remover</ActionButton></div>)}
  </div>;
}

function Docs() {
  const list = useAsync(() => api<any[]>("/documents"));
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [ok, setOk] = useState("");
  useEffect(() => { setOk(""); }, []);
  return <div className="space-y-3">
    <div className="card space-y-3">
      <h2 className="font-semibold">Documentos comerciais (PDF ou TXT, até 5 MB)</h2>
      <p className="text-sm text-slate-500">Cardápios, tabelas de preços, regulamentos. O agente consulta os trechos relevantes de cada pergunta. PDFs escaneados (imagem) não têm texto legível.</p>
      <input type="file" accept="application/pdf,.pdf,.txt,text/plain" disabled={busy} className="block w-full text-sm" onChange={async (e) => {
        const file = e.target.files?.[0]; if (!file) return; setErr(""); setOk(""); setBusy(true);
        try { const r = await upload("/documents", file); setOk(`“${r.filename}” importado (${r.chars} caracteres).`); list.reload(); } catch (x: any) { setErr(x.message); } finally { setBusy(false); e.target.value = ""; }
      }} />
      {busy && <p className="text-sm">Processando…</p>}<Alert>{err}</Alert><Alert kind="ok">{ok}</Alert>
    </div>
    {list.data?.map((d) => <div key={d.id} className="card flex items-center justify-between"><span>📄 {d.filename}</span>
      <ActionButton className="btn-ghost text-sm text-red-600" onClick={async () => { await api(`/documents/${d.id}`, { method: "DELETE" }); list.reload(); }}>Remover</ActionButton></div>)}
  </div>;
}

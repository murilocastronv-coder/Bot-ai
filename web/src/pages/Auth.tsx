import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { Alert, Field } from "../components/ui";

function Shell({ title, children }: { title: string; children: ReactNode }) {
  return <div className="grid min-h-screen place-items-center bg-gradient-to-b from-brand-50 to-white px-4 py-10">
    <div className="w-full max-w-md">
      <Link to="/" className="mb-6 flex items-center justify-center gap-2 text-lg font-extrabold"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-sm text-white">AI</span>SmartBusiness AI</Link>
      <div className="card"><h1 className="mb-4 text-xl font-bold">{title}</h1>{children}</div>
    </div>
  </div>;
}

function useSubmit() {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const run = (fn: () => Promise<void>) => async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await fn(); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  return { busy, err, run, setErr };
}

export function Login() {
  const nav = useNavigate();
  const [q] = useSearchParams();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [unverified, setUnverified] = useState(false); const [info, setInfo] = useState("");
  const s = useSubmit();
  return <Shell title="Entrar">
    <div className="space-y-3">
      {q.get("verified") === "1" && <Alert kind="ok">E-mail confirmado! Agora você pode entrar.</Alert>}
      {q.get("verified") === "0" && <Alert>Link de verificação inválido ou já utilizado.</Alert>}
      <Alert>{s.err}</Alert><Alert kind="ok">{info}</Alert>
      <form className="space-y-3" onSubmit={s.run(async () => {
        try { await api("/auth/login", { body: { email, password } }); nav("/app"); }
        catch (e) { if (e instanceof ApiError && e.code === "EMAIL_NOT_VERIFIED") setUnverified(true); throw e; }
      })}>
        <Field label="E-mail"><input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Senha"><input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <button className="btn-primary w-full" disabled={s.busy}>{s.busy ? "Entrando…" : "Entrar"}</button>
      </form>
      {unverified && <button type="button" className="btn-ghost w-full" onClick={async () => { await api("/auth/resend-verification", { body: { email } }); setInfo("Novo link enviado para o seu e-mail."); }}>Reenviar e-mail de confirmação</button>}
      <div className="flex justify-between text-sm"><Link className="text-brand-600" to="/forgot">Esqueci a senha</Link><Link className="text-brand-600" to="/register">Criar conta</Link></div>
    </div>
  </Shell>;
}

export function Register() {
  const [templates, setTemplates] = useState<{ id: string; label: string }[]>([]);
  const [f, setF] = useState({ name: "", email: "", password: "", businessName: "", template: "services", acceptTerms: false, website: "" });
  const [done, setDone] = useState(false);
  const nav = useNavigate();
  const s = useSubmit();
  useEffect(() => { fetch("/api/public/templates").then((r) => r.json()).then(setTemplates).catch(() => undefined); }, []);
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  if (done) return <Shell title="Verifique seu e-mail"><Alert kind="ok">Enviamos um link de confirmação para <b>{f.email}</b>. Abra-o para ativar sua conta e começar o teste gratuito de 7 dias.</Alert><Link to="/login" className="btn-primary mt-4 w-full">Ir para o login</Link></Shell>;
  return <Shell title="Criar conta — teste grátis de 7 dias">
    <form className="space-y-3" onSubmit={s.run(async () => {
      const r = await api("/auth/register", { body: f });
      if (r.verified) { await api("/auth/login", { body: { email: f.email, password: f.password } }); nav("/app"); return; }
      setDone(true);
    })}>
      <Alert>{s.err}</Alert>
      <Field label="Seu nome"><input className="input" required autoComplete="name" value={f.name} onChange={set("name")} /></Field>
      <Field label="Nome da empresa"><input className="input" required value={f.businessName} onChange={set("businessName")} /></Field>
      <Field label="Tipo de atividade"><select className="input" value={f.template} onChange={set("template")}>{templates.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}</select></Field>
      <Field label="E-mail"><input className="input" type="email" required autoComplete="email" value={f.email} onChange={set("email")} /></Field>
      <Field label="Senha" hint="Mínimo de 10 caracteres."><input className="input" type="password" minLength={10} required autoComplete="new-password" value={f.password} onChange={set("password")} /></Field>
      {/* honeypot anti-spam: invisível para pessoas */}
      <input tabIndex={-1} autoComplete="off" aria-hidden="true" className="absolute -left-[9999px] h-0 w-0" name="website" value={f.website} onChange={set("website")} />
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1 h-5 w-5" required checked={f.acceptTerms} onChange={set("acceptTerms")} /><span>Li e aceito os <Link className="text-brand-600 underline" to="/terms" target="_blank">Termos</Link> e a <Link className="text-brand-600 underline" to="/privacy" target="_blank">Política de privacidade</Link>.</span></label>
      <button className="btn-primary w-full" disabled={s.busy}>{s.busy ? "Criando…" : "Criar conta"}</button>
      <p className="text-center text-sm">Já tem conta? <Link className="text-brand-600" to="/login">Entrar</Link></p>
    </form>
  </Shell>;
}

export function Forgot() {
  const [email, setEmail] = useState(""); const [sent, setSent] = useState(false);
  const s = useSubmit();
  return <Shell title="Recuperar senha">
    {sent ? <Alert kind="ok">Se o e-mail estiver cadastrado, você receberá um link válido por 1 hora.</Alert> :
      <form className="space-y-3" onSubmit={s.run(async () => { await api("/auth/forgot", { body: { email } }); setSent(true); })}>
        <Alert>{s.err}</Alert>
        <Field label="E-mail"><input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <button className="btn-primary w-full" disabled={s.busy}>Enviar link</button>
      </form>}
    <Link to="/login" className="mt-4 block text-center text-sm text-brand-600">Voltar ao login</Link>
  </Shell>;
}

export function Reset() {
  const [q] = useSearchParams(); const nav = useNavigate();
  const [password, setPassword] = useState("");
  const s = useSubmit();
  return <Shell title="Nova senha">
    <form className="space-y-3" onSubmit={s.run(async () => { await api("/auth/reset", { body: { token: q.get("token"), password } }); nav("/login"); })}>
      <Alert>{s.err}</Alert>
      <Field label="Nova senha" hint="Mínimo de 10 caracteres."><input className="input" type="password" minLength={10} required autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      <button className="btn-primary w-full" disabled={s.busy}>Salvar nova senha</button>
    </form>
  </Shell>;
}

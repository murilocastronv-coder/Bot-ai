import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DICTS, initialLang, LANGS, type Lang } from "../lib/i18n";
import { api } from "../lib/api";

const PRICES: Record<string, string> = { FREE: "0 €", STARTER: "19,90 €", PROFESSIONAL: "49,90 €", BUSINESS: "99,90 €" };
const NAMES: Record<string, string> = { FREE: "Free", STARTER: "Starter", PROFESSIONAL: "Professional", BUSINESS: "Business" };

export default function Landing() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [cfg, setCfg] = useState<{ demoWidgetKey?: string; contactEmail?: string }>({});
  const t = DICTS[lang];

  useEffect(() => { document.documentElement.lang = lang; try { localStorage.setItem("sb_lang", lang); } catch { /* ignore */ } }, [lang]);
  useEffect(() => { api("/public/config").then(setCfg).catch(() => undefined); }, []);
  useEffect(() => {
    if (!cfg.demoWidgetKey || document.getElementById("sb-demo-widget")) return;
    const s = document.createElement("script");
    s.id = "sb-demo-widget"; s.src = "/widget.js"; s.async = true; s.setAttribute("data-key", cfg.demoWidgetKey);
    document.body.appendChild(s);
  }, [cfg.demoWidgetKey]);

  const openDemo = () => {
    const host = [...document.querySelectorAll("body > div")].find((d) => (d as HTMLElement).shadowRoot) as HTMLElement | undefined;
    (host?.shadowRoot?.querySelector("button.b") as HTMLButtonElement | null)?.click();
  };

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-extrabold"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-sm text-white">AI</span><span className="hidden sm:inline">SmartBusiness AI</span></Link>
          <nav className="hidden gap-6 text-sm font-medium text-slate-600 md:flex">
            <a href="#features">{t.nav.features}</a><a href="#pricing">{t.nav.pricing}</a><a href="#faq">{t.nav.faq}</a>
          </nav>
          <div className="flex items-center gap-2">
            <select aria-label="Idioma / Langue / Language" className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm" value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
              {LANGS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
            <Link to="/login" className="btn-ghost hidden px-3 sm:inline-flex">{t.nav.login}</Link>
            <Link to="/register" className="btn-primary px-3">{t.nav.trial}</Link>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden bg-gradient-to-b from-brand-900 via-brand-700 to-brand-600 text-white">
        <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] [background-size:24px_24px]" />
        <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-16 md:grid-cols-2 md:py-24">
          <div>
            <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">{t.hero.title}</h1>
            <p className="mt-5 text-lg text-brand-100">{t.hero.sub}</p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/register" className="btn bg-white px-6 py-3 text-brand-700 hover:bg-brand-50">{t.hero.cta}</Link>
              <a href="#demo" className="btn px-6 py-3 ring-1 ring-white/40 hover:bg-white/10">{t.demo.title}</a>
            </div>
            <p className="mt-3 text-sm text-brand-100">{t.hero.note}</p>
            <div className="mt-8 flex flex-wrap gap-2 text-xs font-semibold">
              {["WhatsApp Business", "Telegram", "Website", "Stripe", "OpenAI"].map((c) => <span key={c} className="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20">{c}</span>)}
            </div>
          </div>
          <ExampleChat lang={lang} label={t.demo.illustrative} />
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-center text-3xl font-bold">{t.features.title}</h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {t.features.items.map(([h, p], i) => (
            <div key={h} className="card">
              <div className="mb-3 grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-lg">{["🕐", "📅", "📝", "✅", "🌍", "🙋"][i]}</div>
              <h3 className="font-semibold">{h}</h3><p className="mt-1 text-sm text-slate-600">{p}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-slate-50 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-center text-3xl font-bold">{t.how.title}</h2>
          <ol className="mt-10 grid gap-4 md:grid-cols-3">
            {t.how.steps.map((s, i) => <li key={s} className="card flex items-start gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-600 font-bold text-white">{i + 1}</span><span className="pt-1">{s}</span></li>)}
          </ol>
        </div>
      </section>

      <section id="demo" className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-3xl font-bold">{t.demo.title}</h2>
        {cfg.demoWidgetKey ? (<>
          <p className="mt-3 text-slate-600">{t.demo.sub}</p>
          <button type="button" className="btn-primary mt-6 px-6" onClick={openDemo}>{t.demo.open} 💬</button>
        </>) : (
          <div className="mx-auto mt-6 max-w-md"><ExampleChat lang={lang} label={t.demo.illustrative} light /></div>
        )}
      </section>

      <section id="pricing" className="bg-slate-50 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-center text-3xl font-bold">{t.pricing.title}</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.keys(PRICES).map((p) => (
              <div key={p} className={`card flex flex-col ${p === "PROFESSIONAL" ? "ring-2 ring-brand-600" : ""}`}>
                <h3 className="text-lg font-bold">{NAMES[p]}</h3>
                <p className="mt-2"><span className="text-3xl font-extrabold">{PRICES[p]}</span><span className="text-slate-500">{t.pricing.month}</span></p>
                <ul className="mt-4 flex-1 space-y-2 text-sm">{t.pricing.plans[p].map((f) => <li key={f} className="flex gap-2"><span className="text-brand-600">✓</span>{f}</li>)}</ul>
                <Link to={`/register?plan=${p}`} className={`${p === "PROFESSIONAL" ? "btn-primary" : "btn-ghost"} mt-6`}>{p === "FREE" ? t.nav.trial : t.pricing.choose}</Link>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-sm text-slate-500">{t.pricing.note}</p>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-3xl px-4 py-16">
        <h2 className="text-center text-3xl font-bold">{t.faq.title}</h2>
        <div className="mt-8 space-y-3">
          {t.faq.items.map(([q, a]) => (
            <details key={q} className="card group"><summary className="cursor-pointer list-none font-semibold">{q}<span className="float-right text-brand-600 group-open:rotate-45">+</span></summary><p className="mt-3 text-slate-600">{a}</p></details>
          ))}
        </div>
      </section>

      {cfg.contactEmail && (
        <section className="mx-auto max-w-3xl px-4 pb-16 text-center">
          <div className="card bg-brand-50">
            <h2 className="text-2xl font-bold">{t.contact.title}</h2><p className="mt-2 text-slate-600">{t.contact.sub}</p>
            <a className="btn-primary mt-4" href={`mailto:${cfg.contactEmail}?subject=SmartBusiness%20AI`}>{t.contact.cta}</a>
          </div>
        </section>
      )}

      <footer className="border-t border-slate-100 py-8 text-center text-sm text-slate-500">
        <div className="flex flex-wrap justify-center gap-4"><Link to="/privacy">{t.footer.privacy}</Link><Link to="/terms">{t.footer.terms}</Link></div>
        <p className="mt-3">© {new Date().getFullYear()} SmartBusiness AI</p>
      </footer>
    </div>
  );
}

const EXAMPLE: Record<Lang, [string, string][]> = {
  pt: [["c", "Olá! Vocês têm horário amanhã para corte?"], ["a", "Olá! Tenho horários às 10:00, 14:30 e 16:00 para Corte feminino. Qual prefere?"], ["c", "14:30, por favor. Sou a Ana."], ["a", "Pronto, Ana! Agendado para amanhã às 14:30. Enviaremos um lembrete na véspera."]],
  fr: [["c", "Bonjour ! Vous avez un créneau demain pour une coupe ?"], ["a", "Bonjour ! J’ai 10:00, 14:30 et 16:00 pour une coupe femme. Lequel préférez-vous ?"], ["c", "14:30 s’il vous plaît. C’est Léa."], ["a", "C’est noté, Léa ! Rendez-vous demain à 14:30. Vous recevrez un rappel la veille."]],
  en: [["c", "Hi! Do you have a slot tomorrow for a haircut?"], ["a", "Hi! I have 10:00, 14:30 and 16:00 for a women's cut. Which do you prefer?"], ["c", "14:30 please. I'm Emma."], ["a", "Done, Emma! Booked for tomorrow at 14:30. We'll send you a reminder the day before."]],
  es: [["c", "¡Hola! ¿Tienen hueco mañana para un corte?"], ["a", "¡Hola! Tengo 10:00, 14:30 y 16:00 para corte de mujer. ¿Cuál prefiere?"], ["c", "14:30, por favor. Soy Lucía."], ["a", "¡Listo, Lucía! Reservado para mañana a las 14:30. Le enviaremos un recordatorio."]],
};

function ExampleChat({ lang, label, light }: { lang: Lang; label: string; light?: boolean }) {
  return (
    <figure className={`rounded-3xl p-4 shadow-2xl ${light ? "bg-slate-100" : "bg-white/10 ring-1 ring-white/20"}`}>
      <div className="space-y-2 rounded-2xl bg-white p-4 text-left text-sm text-slate-800">
        {EXAMPLE[lang].map(([r, m], i) => <div key={i} className={`max-w-[85%] rounded-2xl px-3 py-2 ${r === "c" ? "ml-auto rounded-br-sm bg-brand-600 text-white" : "rounded-bl-sm bg-slate-100"}`}>{m}</div>)}
      </div>
      <figcaption className={`mt-2 text-center text-xs ${light ? "text-slate-500" : "text-brand-100"}`}>{label}</figcaption>
    </figure>
  );
}

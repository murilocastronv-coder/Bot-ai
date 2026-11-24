import { createContext, useContext, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

type Me = { id: string; name: string; email: string; role: string };
type RtEvent = { type: string; conversationId?: string; message?: any };
const Ctx = createContext<{ me: Me | null; onEvent: (fn: (e: RtEvent) => void) => () => void }>({ me: null, onEvent: () => () => undefined });
export const useApp = () => useContext(Ctx);

const NAV = [
  ["/app", "Início", "🏠"], ["/app/conversations", "Conversas", "💬"], ["/app/contacts", "CRM", "👥"], ["/app/calendar", "Agenda", "📅"],
  ["/app/agent", "Agente", "🤖"], ["/app/channels", "Canais", "🔌"], ["/app/billing", "Assinatura", "💳"], ["/app/account", "Conta", "⚙️"],
] as const;

export default function AppLayout() {
  const nav = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [waiting, setWaiting] = useState(0);
  const [more, setMore] = useState(false);
  const listeners = useRef(new Set<(e: RtEvent) => void>());

  useEffect(() => { api<Me>("/auth/me").then(setMe).catch(() => nav("/login")); }, [nav]);
  useEffect(() => { if (me) api("/stats").then((s) => setWaiting(s.waitingHuman)).catch(() => undefined); }, [me]);

  // WebSocket com reconexão automática
  useEffect(() => {
    if (!me) return;
    let ws: WebSocket | null = null, stop = false, retry: number | undefined;
    const connect = () => {
      ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
      ws.onmessage = (m) => {
        const e = JSON.parse(m.data);
        if (e.type === "handoff") { setWaiting((w) => w + 1); if ("Notification" in window && Notification.permission === "granted") new Notification("Cliente aguardando atendimento humano"); }
        listeners.current.forEach((fn) => fn(e));
      };
      ws.onclose = () => { if (!stop) retry = window.setTimeout(connect, 3000); };
    };
    connect();
    return () => { stop = true; clearTimeout(retry); ws?.close(); };
  }, [me]);

  const onEvent = (fn: (e: RtEvent) => void) => { listeners.current.add(fn); return () => { listeners.current.delete(fn); }; };
  if (!me) return <div className="p-10 text-center text-slate-500">Carregando…</div>;
  const items = me.role === "SUPERADMIN" ? [...NAV, ["/app/admin", "Admin", "🛡️"] as const] : NAV;

  return <Ctx.Provider value={{ me, onEvent }}>
    <div className="min-h-screen pb-20 lg:flex lg:pb-0">
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white lg:block">
        <div className="flex items-center gap-2 p-5 font-extrabold"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-sm text-white">AI</span>SmartBusiness</div>
        <nav className="space-y-1 px-3">{items.map(([to, label, icon]) => (
          <NavLink key={to} to={to} end={to === "/app"} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"}`}>
            <span>{icon}</span>{label}{to === "/app/conversations" && waiting > 0 && <span className="badge ml-auto bg-red-500 text-white">{waiting}</span>}
          </NavLink>))}
        </nav>
        <button className="m-3 text-sm text-slate-500 hover:text-slate-800" onClick={async () => { await api("/auth/logout", { method: "POST" }); nav("/login"); }}>Sair</button>
      </aside>
      <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6"><Outlet /></main>
      {/* Navegação inferior mobile (Android): 4 atalhos + menu "Mais" */}
      {more && <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setMore(false)}>
        <div className="absolute inset-x-0 bottom-16 grid grid-cols-3 gap-2 rounded-t-3xl bg-white p-4 pb-6" onClick={(e) => e.stopPropagation()}>
          {items.slice(4).map(([to, label, icon]) => <NavLink key={to} to={to} onClick={() => setMore(false)} className="flex flex-col items-center gap-1 rounded-2xl bg-slate-50 p-3 text-sm"><span className="text-xl">{icon}</span>{label}</NavLink>)}
          <button className="flex flex-col items-center gap-1 rounded-2xl bg-slate-50 p-3 text-sm" onClick={async () => { await api("/auth/logout", { method: "POST" }); nav("/login"); }}><span className="text-xl">🚪</span>Sair</button>
        </div>
      </div>}
      <nav className="fixed inset-x-0 bottom-0 z-50 flex border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        {items.slice(0, 4).map(([to, label, icon]) => (
          <NavLink key={to} to={to} end={to === "/app"} onClick={() => setMore(false)} className={({ isActive }) => `relative flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${isActive ? "text-brand-700" : "text-slate-500"}`}>
            <span className="text-lg">{icon}</span>{label}
            {to === "/app/conversations" && waiting > 0 && <span className="absolute right-1/4 top-1 h-2.5 w-2.5 rounded-full bg-red-500" />}
          </NavLink>))}
        <button onClick={() => setMore(!more)} className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${more ? "text-brand-700" : "text-slate-500"}`}><span className="text-lg">☰</span>Mais</button>
      </nav>
    </div>
  </Ctx.Provider>;
}

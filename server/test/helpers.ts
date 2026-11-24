import request from "supertest";
import { vi } from "vitest";
import { createApp } from "../src/app.js";
import { prisma } from "../src/lib/db.js";
import { sentMails } from "../src/lib/mailer.js";

export const app = createApp();

/** Cria e verifica uma conta; devolve um agente supertest autenticado. */
export async function signup(email = `o${Math.random().toString(36).slice(2)}@test.dev`, template = "hairdresser") {
  const agent = request.agent(app);
  await agent.post("/api/auth/register").send({ name: "Dona", email, password: "senha-muito-segura", businessName: "Salão Teste", template, acceptTerms: true }).expect(201);
  const mail = sentMails.filter((m) => m.to === email).pop()!;
  const token = /token=([\w-]+)/.exec(mail.text)![1];
  await agent.get(`/api/auth/verify?token=${token}`).expect(302);
  await agent.post("/api/auth/login").send({ email, password: "senha-muito-segura" }).expect(200);
  const user = await prisma.user.findUniqueOrThrow({ where: { email } });
  return { agent, user, businessId: user.businessId! };
}

export async function setPlan(businessId: string, plan: "FREE" | "STARTER" | "PROFESSIONAL" | "BUSINESS") {
  await prisma.business.update({ where: { id: businessId }, data: { plan, subscriptionStatus: "active" } });
}

type Handler = (url: string, init: RequestInit & { json?: any }) => unknown;
/** Intercepta fetch e responde conforme o host; registra todas as chamadas. */
export function mockFetch(routes: Record<string, Handler>) {
  const calls: { url: string; body: any }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: any, init: any = {}) => {
    const url = String(input);
    const body = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ url, body });
    const key = Object.keys(routes).find((k) => url.includes(k));
    if (!key) throw new Error(`fetch inesperado: ${url}`);
    const out = await routes[key](url, { ...init, json: body });
    return new Response(JSON.stringify(out), { status: 200, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

/** Fila de respostas simuladas do modelo (formato oficial Chat Completions). */
export function openaiScript(steps: ({ text: string } | { tool: string; args: object })[]) {
  let i = 0;
  return () => {
    const s = steps[Math.min(i++, steps.length - 1)];
    const message = "text" in s ? { role: "assistant", content: s.text }
      : { role: "assistant", content: null, tool_calls: [{ id: `call_${i}`, type: "function", function: { name: s.tool, arguments: JSON.stringify(s.args) } }] };
    return { choices: [{ message }], usage: { prompt_tokens: 1000, completion_tokens: 100 } };
  };
}

export function nextWeekday(dayIndexMon0 = 1) { // 0=segunda
  const d = new Date(); d.setUTCDate(d.getUTCDate() + 7);
  while ((d.getUTCDay() + 6) % 7 !== dayIndexMon0) d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

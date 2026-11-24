import type { Channel } from "@prisma/client";
import { prisma } from "../lib/db.js";
import { logError } from "../lib/log.js";
import { monthStart, PLANS, planIsActive } from "../lib/plans.js";
import { bizKey, convKey, publish } from "../lib/realtime.js";
import { buildSystemPrompt, looksLikeInjection, retrieveDocChunks } from "./knowledge.js";
import { detectLanguage } from "./language.js";
import { chatCompletion, costMicroUsd, type ChatMessage } from "./openai.js";
import { formatInTz } from "./time.js";
import { runTool, TOOL_DEFS, type ToolCtx } from "./tools.js";

const FALLBACK: Record<string, string> = {
  pt: "Obrigado pela mensagem! Um membro da nossa equipe responderá em breve.",
  fr: "Merci pour votre message ! Un membre de notre équipe vous répondra bientôt.",
  en: "Thanks for your message! A member of our team will reply shortly.",
  es: "¡Gracias por su mensaje! Un miembro de nuestro equipo le responderá pronto.",
};
const MAX_INPUT = 2000;

export interface IncomingMessage { businessId: string; channel: Channel; externalId: string; text: string; name?: string; phone?: string; languageHint?: string }
export interface AgentOutcome { reply: string | null; conversationId: string; handoff: boolean }

export async function monthlyAiUsage(businessId: string) {
  return prisma.usageRecord.count({ where: { businessId, createdAt: { gte: monthStart() } } });
}

/** Registra a mensagem do cliente (contato + conversa) e devolve o contexto. */
export async function openConversation(m: IncomingMessage) {
  const business = await prisma.business.findUnique({ where: { id: m.businessId } });
  if (!business || business.blocked) return null;
  const text = m.text.slice(0, MAX_INPUT).trim();
  if (!text) return null;

  const contact = await prisma.contact.upsert({
    where: { businessId_channel_externalId: { businessId: business.id, channel: m.channel, externalId: m.externalId } },
    create: { businessId: business.id, channel: m.channel, externalId: m.externalId, name: m.name ?? "", phone: m.phone ?? "", language: m.languageHint && business.languages.includes(m.languageHint) ? m.languageHint : "" },
    update: {},
  });
  const lang = detectLanguage(text, business.languages);
  if (lang && lang !== contact.language) { contact.language = lang; await prisma.contact.update({ where: { id: contact.id }, data: { language: lang } }); }

  let conv = await prisma.conversation.findFirst({ where: { businessId: business.id, contactId: contact.id, status: { not: "CLOSED" } }, orderBy: { lastMessageAt: "desc" } });
  if (!conv) conv = await prisma.conversation.create({ data: { businessId: business.id, contactId: contact.id, channel: m.channel } });
  const saved = await prisma.message.create({ data: { conversationId: conv.id, role: "customer", content: text } });
  await prisma.conversation.update({ where: { id: conv.id }, data: { lastMessageAt: new Date() } });
  publish(bizKey(business.id), { type: "message", conversationId: conv.id, message: saved });
  return { business, contact, conv, text };
}

/** Resposta fixa (sem IA), registrada no histórico como as demais. */
export async function replyDirect(conversationId: string, businessId: string, reply: string, handoff = false) {
  if (handoff) {
    await prisma.conversation.update({ where: { id: conversationId }, data: { status: "HUMAN" } });
    publish(bizKey(businessId), { type: "handoff", conversationId });
  }
  return saveReply(conversationId, businessId, reply, handoff);
}

/** Ponto único de entrada para TODOS os canais (widget, WhatsApp, Telegram). */
export async function handleIncoming(m: IncomingMessage): Promise<AgentOutcome | null> {
  const opened = await openConversation(m);
  if (!opened) return null;
  const { business, contact, conv, text } = opened;

  const result = (reply: string | null, handoff = false): AgentOutcome => ({ reply, conversationId: conv.id, handoff });

  if (conv.status === "HUMAN" || !business.agentEnabled) return result(null);

  const plan = PLANS[business.plan];
  const used = await monthlyAiUsage(business.id);
  if (!planIsActive(business) || used >= plan.aiResponses || !plan.channels.includes(m.channel)) {
    // Sem IA disponível: resposta fixa + transferência para humano (sem custo de IA).
    await prisma.conversation.update({ where: { id: conv.id }, data: { status: "HUMAN" } });
    return saveReply(conv.id, business.id, FALLBACK[contact.language || business.languages[0]] ?? FALLBACK.pt, true);
  }

  if (looksLikeInjection(text)) await logError("prompt-injection-suspect", `conv=${conv.id}: ${text.slice(0, 200)}`, business.id);

  try {
    const [services, faqs, docs, history] = await Promise.all([
      prisma.service.findMany({ where: { businessId: business.id } }),
      prisma.faq.findMany({ where: { businessId: business.id } }),
      prisma.knowledgeDoc.findMany({ where: { businessId: business.id } }),
      prisma.message.findMany({ where: { conversationId: conv.id }, orderBy: { createdAt: "desc" }, take: 20 }),
    ]);
    const system = buildSystemPrompt(business, services, faqs, retrieveDocChunks(docs, text), {
      nowText: formatInTz(new Date(), business.timezone), language: contact.language || null, channel: m.channel,
    });
    const msgs: ChatMessage[] = [{ role: "system", content: system }];
    for (const h of history.reverse()) {
      if (h.role === "customer") msgs.push({ role: "user", content: h.content });
      else if (h.role === "assistant" || h.role === "human") msgs.push({ role: "assistant", content: h.content });
    }
    const ctx: ToolCtx = { business, contact, conversationId: conv.id, services, handoff: false };
    let pin = 0, pout = 0, reply = "";
    for (let i = 0; i < 5; i++) {
      const r = await chatCompletion(msgs, TOOL_DEFS);
      pin += r.promptTokens; pout += r.completionTokens;
      // reenvia só os campos padrão (compatível com OpenAI, Groq e Gemini)
      msgs.push({ role: "assistant", content: r.message.content ?? "", ...(r.message.tool_calls?.length ? { tool_calls: r.message.tool_calls } : {}) });
      if (!r.message.tool_calls?.length) { reply = r.message.content ?? ""; break; }
      for (const call of r.message.tool_calls) {
        const out = await runTool(call.function.name, call.function.arguments, ctx);
        msgs.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(out) });
      }
    }
    await prisma.usageRecord.create({ data: { businessId: business.id, promptTokens: pin, completionTokens: pout, costMicroUsd: costMicroUsd(pin, pout) } });
    if (!reply) reply = FALLBACK[contact.language || business.languages[0]] ?? FALLBACK.pt;
    if (ctx.handoff) publish(bizKey(business.id), { type: "handoff", conversationId: conv.id });
    return saveReply(conv.id, business.id, reply, ctx.handoff);
  } catch (err) {
    await logError("agent", err, business.id);
    await prisma.conversation.update({ where: { id: conv.id }, data: { status: "HUMAN" } });
    publish(bizKey(business.id), { type: "handoff", conversationId: conv.id });
    return saveReply(conv.id, business.id, FALLBACK[contact.language || business.languages[0]] ?? FALLBACK.pt, true);
  }
}

async function saveReply(conversationId: string, businessId: string, reply: string, handoff: boolean): Promise<AgentOutcome> {
  const msg = await prisma.message.create({ data: { conversationId, role: "assistant", content: reply } });
  publish(bizKey(businessId), { type: "message", conversationId, message: msg });
  publish(convKey(conversationId), { type: "message", message: msg });
  return { reply, conversationId, handoff };
}

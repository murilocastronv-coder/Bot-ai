import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH } from "../lib/auth.js";
import { bizKey, publish } from "../lib/realtime.js";
import { sendToContact } from "../channels/send.js";
import { logError } from "../lib/log.js";

export const crmRouter = Router();

// ---- Conversas e atendimento humano ----
crmRouter.get("/conversations", asyncH(async (req, res) => {
  const status = z.enum(["BOT", "HUMAN", "CLOSED"]).optional().parse(req.query.status || undefined);
  const list = await prisma.conversation.findMany({
    where: { businessId: req.businessId, ...(status ? { status } : {}) }, orderBy: { lastMessageAt: "desc" }, take: 100,
    include: { contact: true, messages: { orderBy: { createdAt: "desc" }, take: 1 } },
  });
  res.json(list);
}));
crmRouter.get("/conversations/:id", asyncH(async (req, res) => {
  const c = await prisma.conversation.findFirst({ where: { id: req.params.id, businessId: req.businessId }, include: { contact: true, messages: { orderBy: { createdAt: "asc" }, take: 500 } } });
  if (!c) return res.status(404).json({ error: "Não encontrado" });
  res.json(c);
}));
crmRouter.post("/conversations/:id/reply", asyncH(async (req, res) => {
  const { text } = z.object({ text: z.string().min(1).max(4000) }).parse(req.body);
  const c = await prisma.conversation.findFirst({ where: { id: req.params.id, businessId: req.businessId }, include: { contact: true, business: true } });
  if (!c) return res.status(404).json({ error: "Não encontrado" });
  const msg = await prisma.message.create({ data: { conversationId: c.id, role: "human", content: text } });
  await prisma.conversation.update({ where: { id: c.id }, data: { status: "HUMAN", lastMessageAt: new Date() } });
  try { await sendToContact(c.business, c.contact, c.id, text, msg); }
  catch (e) { await logError("human-reply", e, c.businessId); return res.status(502).json({ error: `Mensagem salva, mas o envio falhou: ${(e as Error).message}` }); }
  publish(bizKey(c.businessId), { type: "message", conversationId: c.id, message: msg });
  res.json(msg);
}));
crmRouter.post("/conversations/:id/status", asyncH(async (req, res) => {
  const { status } = z.object({ status: z.enum(["BOT", "HUMAN", "CLOSED"]) }).parse(req.body);
  const r = await prisma.conversation.updateMany({ where: { id: req.params.id, businessId: req.businessId }, data: { status } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));

// ---- Contatos ----
const contactPatch = z.object({
  name: z.string().max(120), phone: z.string().max(40), email: z.string().max(200), serviceInterest: z.string().max(200),
  status: z.enum(["NEW", "LEAD", "QUALIFIED", "CUSTOMER", "LOST"]), notes: z.string().max(5000), marketingConsent: z.boolean(),
}).partial();
crmRouter.get("/contacts", asyncH(async (req, res) => {
  const q = String(req.query.q ?? "").slice(0, 100);
  res.json(await prisma.contact.findMany({
    where: { businessId: req.businessId, ...(q ? { OR: [{ name: { contains: q, mode: "insensitive" } }, { phone: { contains: q } }, { email: { contains: q, mode: "insensitive" } }] } : {}) },
    orderBy: { updatedAt: "desc" }, take: 500,
    include: { _count: { select: { bookings: true, quotes: true, conversations: true } } },
  }));
}));
crmRouter.patch("/contacts/:id", asyncH(async (req, res) => {
  const d = contactPatch.parse(req.body);
  const data: any = { ...d };
  if (d.marketingConsent !== undefined) data.consentAt = new Date();
  const r = await prisma.contact.updateMany({ where: { id: req.params.id, businessId: req.businessId }, data });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));
/** Direito ao apagamento (RGPD art. 17) de um cliente final. */
crmRouter.delete("/contacts/:id", asyncH(async (req, res) => {
  const r = await prisma.contact.deleteMany({ where: { id: req.params.id, businessId: req.businessId } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));
/** Exportação de dados de um cliente final (RGPD art. 15/20). */
crmRouter.get("/contacts/:id/export", asyncH(async (req, res) => {
  const c = await prisma.contact.findFirst({ where: { id: req.params.id, businessId: req.businessId }, include: { conversations: { include: { messages: true } }, bookings: true, quotes: true } });
  if (!c) return res.status(404).json({ error: "Não encontrado" });
  res.setHeader("content-disposition", `attachment; filename="contato-${c.id}.json"`);
  res.json(c);
}));

const csvCell = (v: unknown) => {
  let s = v == null ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s; // evita injeção de fórmulas no Excel
  return `"${s.replace(/"/g, '""')}"`;
};
crmRouter.get("/contacts.csv", asyncH(async (req, res) => {
  const list = await prisma.contact.findMany({ where: { businessId: req.businessId }, orderBy: { createdAt: "asc" } });
  const header = ["nome", "telefone", "email", "canal", "idioma", "servico", "status", "consentimento_marketing", "data_consentimento", "criado_em"];
  const rows = list.map((c) => [c.name, c.phone, c.email, c.channel, c.language, c.serviceInterest, c.status, c.marketingConsent ? "sim" : "nao", c.consentAt?.toISOString() ?? "", c.createdAt.toISOString()].map(csvCell).join(","));
  res.setHeader("content-type", "text/csv; charset=utf-8");
  res.setHeader("content-disposition", 'attachment; filename="contatos.csv"');
  res.send("﻿" + [header.join(","), ...rows].join("\r\n"));
}));

// ---- Orçamentos e agendamentos ----
crmRouter.get("/quotes", asyncH(async (req, res) => res.json(await prisma.quoteRequest.findMany({ where: { businessId: req.businessId }, include: { contact: true }, orderBy: { createdAt: "desc" }, take: 200 }))));
crmRouter.patch("/quotes/:id", asyncH(async (req, res) => {
  const { status } = z.object({ status: z.enum(["open", "sent", "won", "lost"]) }).parse(req.body);
  const r = await prisma.quoteRequest.updateMany({ where: { id: req.params.id, businessId: req.businessId }, data: { status } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));
crmRouter.get("/bookings", asyncH(async (req, res) => {
  const from = req.query.from ? new Date(String(req.query.from)) : new Date(Date.now() - 7 * 86400000);
  const to = req.query.to ? new Date(String(req.query.to)) : new Date(Date.now() + 60 * 86400000);
  res.json(await prisma.booking.findMany({ where: { businessId: req.businessId, startsAt: { gte: from, lte: to } }, include: { contact: true }, orderBy: { startsAt: "asc" } }));
}));
crmRouter.post("/bookings/:id/cancel", asyncH(async (req, res) => {
  const r = await prisma.booking.updateMany({ where: { id: req.params.id, businessId: req.businessId }, data: { status: "CANCELLED" } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));

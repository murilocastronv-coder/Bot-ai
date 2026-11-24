import { Router } from "express";
import rateLimit from "express-rate-limit";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH } from "../lib/auth.js";
import { config } from "../lib/config.js";
import { handleIncoming } from "../agent/engine.js";

/** API pública do widget. Identificação: widgetKey (público) + sessionId aleatório do navegador. */
export const widgetRouter = Router();
const limiter = rateLimit({ windowMs: 60000, limit: config.isProd ? 20 : 1000, standardHeaders: true, legacyHeaders: false, keyGenerator: (req) => `${req.ip}:${req.params.key}` });
const session = z.string().regex(/^[A-Za-z0-9_-]{16,64}$/);

widgetRouter.use((req, res, next) => { res.setHeader("access-control-allow-origin", "*"); res.setHeader("access-control-allow-headers", "content-type"); if (req.method === "OPTIONS") return res.sendStatus(204); next(); });

widgetRouter.get("/:key/info", asyncH(async (req, res) => {
  const b = await prisma.business.findUnique({ where: { widgetKey: req.params.key } });
  if (!b || b.blocked) return res.status(404).json({ error: "Widget não encontrado" });
  res.json({ name: b.name, languages: b.languages, online: b.agentEnabled });
}));

widgetRouter.post("/:key/messages", limiter, asyncH(async (req, res) => {
  const d = z.object({ sessionId: session, text: z.string().min(1).max(2000), hp: z.string().max(0).optional() }).parse(req.body);
  const b = await prisma.business.findUnique({ where: { widgetKey: req.params.key } });
  if (!b || b.blocked) return res.status(404).json({ error: "Widget não encontrado" });
  const out = await handleIncoming({ businessId: b.id, channel: "WIDGET", externalId: d.sessionId, text: d.text });
  res.json({ reply: out?.reply ?? null, handoff: out?.handoff ?? false });
}));

/** Polling de mensagens (para receber respostas do atendente humano). */
widgetRouter.get("/:key/messages", asyncH(async (req, res) => {
  const sid = session.parse(req.query.sessionId);
  const after = req.query.after ? new Date(String(req.query.after)) : new Date(0);
  const b = await prisma.business.findUnique({ where: { widgetKey: req.params.key } });
  if (!b) return res.status(404).json({ error: "Widget não encontrado" });
  const contact = await prisma.contact.findUnique({ where: { businessId_channel_externalId: { businessId: b.id, channel: "WIDGET", externalId: sid } } });
  if (!contact) return res.json([]);
  const msgs = await prisma.message.findMany({ where: { conversation: { contactId: contact.id, businessId: b.id }, createdAt: { gt: after } }, orderBy: { createdAt: "asc" }, take: 100, select: { id: true, role: true, content: true, createdAt: true } });
  res.json(msgs);
}));

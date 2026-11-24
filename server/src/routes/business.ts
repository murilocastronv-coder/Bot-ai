import { Router } from "express";
import multer from "multer";
import { z } from "zod";
import { PDFParse } from "pdf-parse";
import { prisma } from "../lib/db.js";
import { asyncH } from "../lib/auth.js";
import { config } from "../lib/config.js";
import { randomToken, encrypt, decrypt } from "../lib/crypto.js";
import { monthStart, PLANS, planIsActive } from "../lib/plans.js";
import { DAY_KEYS } from "../agent/time.js";
import { getTemplate, TEMPLATES } from "../agent/templates.js";
import { telegram } from "../channels/telegram.js";
import { registerBotCommands } from "../channels/telegram-menu.js";
import { verifyWhatsAppCredentials } from "../channels/whatsapp.js";
import { monthlyAiUsage } from "../agent/engine.js";

export const businessRouter = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

const timeRe = /^([01]\d|2[0-3]):[0-5]\d$/;
const hoursSchema = z.object(Object.fromEntries(DAY_KEYS.map((d) => [d, z.array(z.tuple([z.string().regex(timeRe), z.string().regex(timeRe)])).max(4).optional()])));
const businessSchema = z.object({
  name: z.string().min(1).max(160), template: z.enum(TEMPLATES.map((t) => t.id) as [string, ...string[]]),
  address: z.string().max(300), phone: z.string().max(40), openingHours: hoursSchema,
  personality: z.string().max(500), languages: z.array(z.enum(["pt", "fr", "en", "es"])).min(1),
  customInstructions: z.string().max(4000), timezone: z.string().max(60).refine((tz) => { try { new Intl.DateTimeFormat("en", { timeZone: tz }); return true; } catch { return false; } }, "Fuso inválido"),
  slotMinutes: z.number().int().min(10).max(240),
}).partial();

function publicBusiness(b: any) {
  const { telegramBotTokenEnc, waAccessTokenEnc, telegramWebhookSecret, ...rest } = b;
  return { ...rest, telegramConnected: !!telegramBotTokenEnc, whatsappConnected: !!waAccessTokenEnc };
}

businessRouter.get("/templates", (_req, res) => res.json(TEMPLATES));

businessRouter.get("/business", asyncH(async (req, res) => {
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  res.json({ ...publicBusiness(b), planDef: PLANS[b.plan], planActive: planIsActive(b), aiUsedThisMonth: await monthlyAiUsage(b.id), template: b.template, templateDef: getTemplate(b.template), widgetKey: b.widgetKey });
}));

businessRouter.put("/business", asyncH(async (req, res) => {
  const d = businessSchema.parse(req.body);
  const b = await prisma.business.update({ where: { id: req.businessId }, data: d });
  res.json(publicBusiness(b));
}));

businessRouter.post("/business/agent", asyncH(async (req, res) => {
  const { enabled } = z.object({ enabled: z.boolean() }).parse(req.body);
  const b = await prisma.business.update({ where: { id: req.businessId }, data: { agentEnabled: enabled } });
  res.json({ agentEnabled: b.agentEnabled });
}));

// ---- Serviços ----
const serviceSchema = z.object({
  name: z.string().min(1).max(160), description: z.string().max(1000).default(""),
  priceCents: z.number().int().min(0).max(100000000).nullable().default(null), priceNote: z.string().max(200).default(""),
  durationMin: z.number().int().min(5).max(1440).default(30), bookable: z.boolean().default(true),
});
businessRouter.get("/services", asyncH(async (req, res) => res.json(await prisma.service.findMany({ where: { businessId: req.businessId }, orderBy: { name: "asc" } }))));
businessRouter.post("/services", asyncH(async (req, res) => res.status(201).json(await prisma.service.create({ data: { ...serviceSchema.parse(req.body), businessId: req.businessId! } }))));
businessRouter.put("/services/:id", asyncH(async (req, res) => {
  const r = await prisma.service.updateMany({ where: { id: req.params.id, businessId: req.businessId }, data: serviceSchema.partial().parse(req.body) });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));
businessRouter.delete("/services/:id", asyncH(async (req, res) => {
  const r = await prisma.service.deleteMany({ where: { id: req.params.id, businessId: req.businessId } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));

// ---- FAQ ----
const faqSchema = z.object({ question: z.string().min(1).max(500), answer: z.string().min(1).max(3000) });
businessRouter.get("/faqs", asyncH(async (req, res) => res.json(await prisma.faq.findMany({ where: { businessId: req.businessId } }))));
businessRouter.post("/faqs", asyncH(async (req, res) => res.status(201).json(await prisma.faq.create({ data: { ...faqSchema.parse(req.body), businessId: req.businessId! } }))));
businessRouter.delete("/faqs/:id", asyncH(async (req, res) => {
  const r = await prisma.faq.deleteMany({ where: { id: req.params.id, businessId: req.businessId } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));

// ---- Documentos (PDF/TXT) ----
businessRouter.get("/documents", asyncH(async (req, res) => res.json(await prisma.knowledgeDoc.findMany({ where: { businessId: req.businessId }, select: { id: true, filename: true, createdAt: true } }))));
businessRouter.post("/documents", upload.single("file"), asyncH(async (req, res) => {
  const f = req.file;
  if (!f) return res.status(400).json({ error: "Arquivo ausente" });
  let text = "";
  if (f.mimetype === "application/pdf" || f.originalname.toLowerCase().endsWith(".pdf")) {
    const parser = new PDFParse({ data: new Uint8Array(f.buffer) });
    try { text = (await parser.getText()).text; } finally { await parser.destroy(); }
  } else if (f.mimetype.startsWith("text/") || /\.(txt|md)$/i.test(f.originalname)) text = f.buffer.toString("utf8");
  else return res.status(400).json({ error: "Envie PDF ou TXT" });
  text = text.replace(/\u0000/g, "").trim().slice(0, 200000);
  if (!text) return res.status(400).json({ error: "Não foi possível extrair texto (PDF escaneado?)" });
  const count = await prisma.knowledgeDoc.count({ where: { businessId: req.businessId } });
  if (count >= 20) return res.status(400).json({ error: "Limite de 20 documentos" });
  const doc = await prisma.knowledgeDoc.create({ data: { businessId: req.businessId!, filename: f.originalname.slice(0, 200), content: text } });
  res.status(201).json({ id: doc.id, filename: doc.filename, chars: text.length });
}));
businessRouter.delete("/documents/:id", asyncH(async (req, res) => {
  const r = await prisma.knowledgeDoc.deleteMany({ where: { id: req.params.id, businessId: req.businessId } });
  res.status(r.count ? 200 : 404).json({ ok: !!r.count });
}));

// ---- Canais ----
businessRouter.post("/channels/telegram", asyncH(async (req, res) => {
  const { token } = z.object({ token: z.string().regex(/^\d+:[A-Za-z0-9_-]{30,}$/, "Token do BotFather inválido") }).parse(req.body);
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  if (!PLANS[b.plan].channels.includes("TELEGRAM")) return res.status(402).json({ error: "Telegram disponível a partir do plano Professional" });
  const me = await telegram.getMe(token).catch((e) => { throw Object.assign(new Error(`Token recusado pelo Telegram: ${e.message}`), { status: 400 }); });
  const secret = randomToken(24);
  await telegram.setWebhook(token, `${config.appUrl}/webhooks/telegram/${b.id}`, secret);
  await registerBotCommands(token).catch(() => undefined);
  await prisma.business.update({ where: { id: b.id }, data: { telegramBotTokenEnc: encrypt(token), telegramBotUsername: me.username, telegramWebhookSecret: secret } });
  res.json({ ok: true, username: me.username });
}));
businessRouter.delete("/channels/telegram", asyncH(async (req, res) => {
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  if (b.telegramBotTokenEnc) await telegram.deleteWebhook(decrypt(b.telegramBotTokenEnc)).catch(() => undefined);
  await prisma.business.update({ where: { id: b.id }, data: { telegramBotTokenEnc: null, telegramBotUsername: null, telegramWebhookSecret: null } });
  res.json({ ok: true });
}));
businessRouter.post("/channels/whatsapp", asyncH(async (req, res) => {
  const d = z.object({ phoneNumberId: z.string().regex(/^\d{5,30}$/), accessToken: z.string().min(20).max(1000) }).parse(req.body);
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  if (!PLANS[b.plan].channels.includes("WHATSAPP")) return res.status(402).json({ error: "WhatsApp disponível a partir do plano Starter" });
  const info = await verifyWhatsAppCredentials(d.phoneNumberId, d.accessToken).catch((e) => { throw Object.assign(e, { status: 400 }); });
  const taken = await prisma.business.findFirst({ where: { waPhoneNumberId: d.phoneNumberId, NOT: { id: b.id } } });
  if (taken) return res.status(409).json({ error: "Este número já está conectado a outra conta" });
  await prisma.business.update({ where: { id: b.id }, data: { waPhoneNumberId: d.phoneNumberId, waAccessTokenEnc: encrypt(d.accessToken) } });
  res.json({ ok: true, ...info, webhookUrl: `${config.appUrl}/webhooks/whatsapp` });
}));
businessRouter.delete("/channels/whatsapp", asyncH(async (req, res) => {
  await prisma.business.update({ where: { id: req.businessId }, data: { waPhoneNumberId: null, waAccessTokenEnc: null } });
  res.json({ ok: true });
}));

// ---- Estatísticas ----
businessRouter.get("/stats", asyncH(async (req, res) => {
  const businessId = req.businessId!;
  const since = monthStart();
  const [messages, contacts, newLeads, bookings, open, human, customers, usage] = await Promise.all([
    prisma.message.count({ where: { role: "customer", conversation: { businessId }, createdAt: { gte: since } } }),
    prisma.contact.count({ where: { businessId, createdAt: { gte: since } } }),
    prisma.contact.count({ where: { businessId, status: { in: ["LEAD", "QUALIFIED"] }, createdAt: { gte: since } } }),
    prisma.booking.count({ where: { businessId, status: "CONFIRMED", createdAt: { gte: since } } }),
    prisma.conversation.count({ where: { businessId, status: { not: "CLOSED" } } }),
    prisma.conversation.count({ where: { businessId, status: "HUMAN" } }),
    prisma.contact.count({ where: { businessId, status: "CUSTOMER", createdAt: { gte: since } } }),
    prisma.usageRecord.aggregate({ where: { businessId, createdAt: { gte: since } }, _count: true, _sum: { promptTokens: true, completionTokens: true, costMicroUsd: true } }),
  ]);
  res.json({
    month: since.toISOString().slice(0, 7), messagesReceived: messages, contactsServed: contacts, newLeads, bookings,
    openConversations: open, waitingHuman: human, conversionRate: contacts ? Math.round((customers / contacts) * 1000) / 10 : 0,
    ai: { responses: usage._count, promptTokens: usage._sum.promptTokens ?? 0, completionTokens: usage._sum.completionTokens ?? 0, costUsd: (usage._sum.costMicroUsd ?? 0) / 1e6 },
  });
}));

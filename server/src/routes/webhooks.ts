import { Router, type Request, type Response } from "express";
import { prisma } from "../lib/db.js";
import { config } from "../lib/config.js";
import { decrypt, safeEqual } from "../lib/crypto.js";
import { logError } from "../lib/log.js";
import { handleIncoming } from "../agent/engine.js";
import { telegram } from "../channels/telegram.js";
import { handleMenu } from "../channels/telegram-menu.js";
import { sendWhatsAppText, verifyMetaSignature } from "../channels/whatsapp.js";

export const webhooksRouter = Router();

async function firstTime(id: string) {
  try { await prisma.processedWebhook.create({ data: { id } }); return true; } catch { return false; }
}

const START: Record<string, string> = { pt: "Olá!", fr: "Bonjour !", en: "Hello!", es: "¡Hola!" };

// ---------- Telegram Bot API ----------
webhooksRouter.post("/telegram/:businessId", async (req: Request, res: Response) => {
  const b = await prisma.business.findUnique({ where: { id: req.params.businessId } });
  const header = String(req.headers["x-telegram-bot-api-secret-token"] ?? "");
  if (!b?.telegramWebhookSecret || !b.telegramBotTokenEnc || !safeEqual(header, b.telegramWebhookSecret)) return res.sendStatus(401);
  const msg = req.body?.message;
  res.sendStatus(200); // responde já; o processamento continua
  if (!msg?.chat?.id || typeof msg.text !== "string" || msg.chat.type !== "private") return;
  if (!(await firstTime(`tg:${b.id}:${req.body.update_id}`))) return;
  const token = decrypt(b.telegramBotTokenEnc);
  const chatId = String(msg.chat.id);
  const lc = String(msg.from?.language_code ?? "pt").slice(0, 2);
  const name = [msg.from?.first_name, msg.from?.last_name].filter(Boolean).join(" ");
  try {
    await telegram.sendChatAction(token, chatId);
    // Menu (botões e comandos): /start, Serviços, Horários, FAQ, Atendente... respondidos sem IA
    const menu = await handleMenu(b.id, chatId, msg.text, lc, name);
    if (menu) {
      const extra: Record<string, unknown> = { reply_markup: menu.keyboard };
      if (menu.markdown) extra.parse_mode = "Markdown";
      await telegram.sendMessage(token, chatId, menu.reply, extra).catch(() => telegram.sendMessage(token, chatId, menu.reply, { reply_markup: menu.keyboard }));
      return;
    }
    const text = msg.text.startsWith("/") ? (START[b.languages[0]] ?? START.pt) : msg.text;
    const out = await handleIncoming({ businessId: b.id, channel: "TELEGRAM", externalId: chatId, text, name, languageHint: b.languages[0] });
    if (out?.reply) await telegram.sendMessage(token, chatId, out.reply);
  } catch (e) { await logError("telegram-webhook", e, b.id); }
});

// ---------- WhatsApp Business Cloud API ----------
webhooksRouter.get("/whatsapp", (req, res) => {
  const ok = req.query["hub.mode"] === "subscribe" && config.waVerifyToken && req.query["hub.verify_token"] === config.waVerifyToken;
  if (ok) return res.status(200).send(String(req.query["hub.challenge"] ?? ""));
  res.sendStatus(403);
});

webhooksRouter.post("/whatsapp", async (req: Request, res: Response) => {
  const raw = req.body as Buffer;
  if (!verifyMetaSignature(raw, req.headers["x-hub-signature-256"] as string | undefined)) return res.sendStatus(401);
  res.sendStatus(200);
  let body: any;
  try { body = JSON.parse(raw.toString("utf8")); } catch { return; }
  for (const entry of body.entry ?? []) for (const change of entry.changes ?? []) {
    const v = change.value;
    if (!v?.messages?.length) continue;
    const b = await prisma.business.findUnique({ where: { waPhoneNumberId: String(v.metadata?.phone_number_id ?? "") } });
    if (!b?.waAccessTokenEnc) continue;
    const token = decrypt(b.waAccessTokenEnc);
    for (const m of v.messages) {
      if (!(await firstTime(`wa:${m.id}`))) continue;
      const text = m.type === "text" ? m.text?.body : m.type === "interactive" ? (m.interactive?.button_reply?.title ?? m.interactive?.list_reply?.title) : null;
      if (!text) continue;
      const name = v.contacts?.find((c: any) => c.wa_id === m.from)?.profile?.name;
      try {
        const out = await handleIncoming({ businessId: b.id, channel: "WHATSAPP", externalId: m.from, text, name, phone: `+${m.from}` });
        if (out?.reply) await sendWhatsAppText(b.waPhoneNumberId!, token, m.from, out.reply);
      } catch (e) { await logError("whatsapp-webhook", e, b.id); }
    }
  }
});

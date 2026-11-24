import { Router } from "express";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH, COOKIE } from "../lib/auth.js";
import { getStripe } from "../services/stripe.js";
import { logError } from "../lib/log.js";

export const accountRouter = Router();

/** Exportação completa dos dados da empresa (RGPD art. 20). */
accountRouter.get("/account/export", asyncH(async (req, res) => {
  const b = await prisma.business.findUniqueOrThrow({
    where: { id: req.businessId },
    include: { users: { select: { id: true, name: true, email: true, role: true, createdAt: true } }, services: true, faqs: true, documents: true, contacts: { include: { conversations: { include: { messages: true } }, bookings: true, quotes: true } } },
  });
  const { telegramBotTokenEnc, waAccessTokenEnc, telegramWebhookSecret, ...safe } = b;
  res.setHeader("content-disposition", 'attachment; filename="smartbusiness-export.json"');
  res.json(safe);
}));

/** Exclusão definitiva da conta e de todos os dados (RGPD art. 17). */
accountRouter.delete("/account", asyncH(async (req, res) => {
  const { password } = z.object({ password: z.string() }).parse(req.body);
  if (!(await bcrypt.compare(password, req.user!.passwordHash))) return res.status(401).json({ error: "Senha incorreta" });
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  const stripe = getStripe();
  if (stripe && b.stripeSubscriptionId) await stripe.subscriptions.cancel(b.stripeSubscriptionId).catch((e) => logError("account-delete", e, b.id));
  await prisma.business.delete({ where: { id: b.id } }); // cascata apaga usuários, contatos, mensagens...
  res.clearCookie(COOKIE, { path: "/" });
  res.json({ ok: true });
}));

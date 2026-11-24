import bcrypt from "bcryptjs";
import { prisma } from "../lib/db.js";
import { config } from "../lib/config.js";
import { encrypt, decrypt, randomToken } from "../lib/crypto.js";
import { logError } from "../lib/log.js";
import { telegram } from "../channels/telegram.js";
import { getTemplate } from "../agent/templates.js";

/**
 * Configuração inicial opcional via variáveis de ambiente (útil no primeiro deploy):
 *  BOOTSTRAP_OWNER_EMAIL / BOOTSTRAP_OWNER_PASSWORD  → cria a conta do dono (SUPERADMIN, plano Business)
 *  BOOTSTRAP_BUSINESS_NAME / BOOTSTRAP_TEMPLATE       → nome e tipo do negócio
 *  TELEGRAM_BOT_TOKEN                                 → conecta o bot do Telegram a esse negócio
 * Idempotente: pode rodar a cada inicialização.
 */
export async function runBootstrap() {
  const email = process.env.BOOTSTRAP_OWNER_EMAIL?.trim().toLowerCase();
  const password = process.env.BOOTSTRAP_OWNER_PASSWORD;
  if (!email || !password) return;
  try {
    let user = await prisma.user.findUnique({ where: { email } });
    if (!user) {
      const business = await prisma.business.create({ data: {
        name: process.env.BOOTSTRAP_BUSINESS_NAME || "Meu negócio",
        template: getTemplate(process.env.BOOTSTRAP_TEMPLATE || "services").id,
        plan: "BUSINESS", subscriptionStatus: "active", trialEndsAt: new Date(Date.now() + 3650 * 86400000),
        openingHours: { mon: [["09:00", "18:00"]], tue: [["09:00", "18:00"]], wed: [["09:00", "18:00"]], thu: [["09:00", "18:00"]], fri: [["09:00", "18:00"]] },
      } });
      user = await prisma.user.create({ data: { email, name: "Administrador", passwordHash: await bcrypt.hash(password, 12), role: "SUPERADMIN", emailVerifiedAt: new Date(), businessId: business.id } });
      console.log(`[bootstrap] conta ${email} e negócio "${business.name}" criados`);
    }
    const token = process.env.TELEGRAM_BOT_TOKEN?.trim();
    if (!token || !user.businessId) return;
    const b = await prisma.business.findUniqueOrThrow({ where: { id: user.businessId } });
    const sameToken = b.telegramBotTokenEnc && decrypt(b.telegramBotTokenEnc) === token;
    const url = `${config.appUrl}/webhooks/telegram/${b.id}`;
    const info = sameToken ? await fetch(`${config.telegramApiBase}/bot${token}/getWebhookInfo`).then((r) => r.json()).catch(() => null) as any : null;
    if (sameToken && info?.result?.url === url) return; // já conectado
    const me = await telegram.getMe(token);
    const secret = sameToken && b.telegramWebhookSecret ? b.telegramWebhookSecret : randomToken(24);
    await telegram.setWebhook(token, url, secret);
    await prisma.business.update({ where: { id: b.id }, data: { telegramBotTokenEnc: encrypt(token), telegramBotUsername: me.username, telegramWebhookSecret: secret } });
    console.log(`[bootstrap] bot @${me.username} conectado ao webhook ${url}`);
  } catch (e) { await logError("bootstrap", e); }
}

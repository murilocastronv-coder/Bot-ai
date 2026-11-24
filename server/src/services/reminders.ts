import { prisma } from "../lib/db.js";
import { logError } from "../lib/log.js";
import { sendToContact } from "../channels/send.js";
import { formatInTz } from "../agent/time.js";

const TXT: Record<string, (s: string, w: string, b: string) => string> = {
  pt: (s, w, b) => `Lembrete: você tem ${s} em ${b} — ${w}. Para cancelar ou remarcar, responda esta mensagem.`,
  fr: (s, w, b) => `Rappel : vous avez ${s} chez ${b} — ${w}. Pour annuler ou modifier, répondez à ce message.`,
  en: (s, w, b) => `Reminder: you have ${s} at ${b} — ${w}. To cancel or reschedule, reply to this message.`,
  es: (s, w, b) => `Recordatorio: tiene ${s} en ${b} — ${w}. Para cancelar o cambiar, responda a este mensaje.`,
};
const LOCALE: Record<string, string> = { pt: "pt-BR", fr: "fr-FR", en: "en-GB", es: "es-ES" };

/** Envia lembretes para agendamentos nas próximas 24h. Executado periodicamente. */
export async function sendDueReminders(now = new Date()) {
  const due = await prisma.booking.findMany({
    where: { status: "CONFIRMED", reminderSent: false, startsAt: { gt: now, lte: new Date(now.getTime() + 24 * 3600000) } },
    include: { contact: true, business: true }, take: 200,
  });
  let sent = 0;
  for (const bk of due) {
    // marca antes de enviar para nunca duplicar
    const claimed = await prisma.booking.updateMany({ where: { id: bk.id, reminderSent: false }, data: { reminderSent: true } });
    if (!claimed.count || bk.business.blocked) continue;
    const lang = bk.contact.language || "pt";
    const text = (TXT[lang] ?? TXT.pt)(bk.serviceName, formatInTz(bk.startsAt, bk.business.timezone, LOCALE[lang] ?? "pt-BR"), bk.business.name);
    const conv = await prisma.conversation.findFirst({ where: { contactId: bk.contactId }, orderBy: { lastMessageAt: "desc" }, include: { messages: { where: { role: "customer" }, orderBy: { createdAt: "desc" }, take: 1 } } });
    if (!conv) continue;
    // WhatsApp só permite texto livre na janela de 24h desde a última mensagem do cliente
    if (bk.contact.channel === "WHATSAPP" && (!conv.messages[0] || now.getTime() - conv.messages[0].createdAt.getTime() > 24 * 3600000)) {
      await logError("reminder", `Fora da janela de 24h do WhatsApp (requer template aprovado) booking=${bk.id}`, bk.businessId);
      continue;
    }
    try {
      const msg = await prisma.message.create({ data: { conversationId: conv.id, role: "assistant", content: text } });
      await sendToContact(bk.business, bk.contact, conv.id, text, msg);
      sent++;
    } catch (e) { await logError("reminder", e, bk.businessId); }
  }
  return sent;
}

export function startReminderLoop() {
  const run = () => sendDueReminders().catch((e) => logError("reminder-loop", e));
  setTimeout(run, 15000);
  return setInterval(run, 10 * 60000);
}

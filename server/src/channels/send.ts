import type { Business, Contact } from "@prisma/client";
import { decrypt } from "../lib/crypto.js";
import { convKey, publish } from "../lib/realtime.js";
import { telegram } from "./telegram.js";
import { sendWhatsAppText } from "./whatsapp.js";

/** Envia texto ao cliente pelo canal de origem. Widget recebe via WebSocket/polling. */
export async function sendToContact(b: Business, contact: Contact, conversationId: string, text: string, message?: unknown) {
  if (contact.channel === "TELEGRAM") {
    if (!b.telegramBotTokenEnc) throw new Error("Telegram não conectado");
    await telegram.sendMessage(decrypt(b.telegramBotTokenEnc), contact.externalId, text);
  } else if (contact.channel === "WHATSAPP") {
    if (!b.waPhoneNumberId || !b.waAccessTokenEnc) throw new Error("WhatsApp não conectado");
    await sendWhatsAppText(b.waPhoneNumberId, decrypt(b.waAccessTokenEnc), contact.externalId, text);
  } else {
    publish(convKey(conversationId), { type: "message", message });
  }
}

import crypto from "node:crypto";
import { config } from "../lib/config.js";

/** Verifica X-Hub-Signature-256 da Meta usando o App Secret. */
export function verifyMetaSignature(rawBody: Buffer, header: string | undefined): boolean {
  if (!config.waAppSecret || !header?.startsWith("sha256=")) return false;
  const expected = "sha256=" + crypto.createHmac("sha256", config.waAppSecret).update(rawBody).digest("hex");
  const a = Buffer.from(expected), b = Buffer.from(header);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export async function sendWhatsAppText(phoneNumberId: string, accessToken: string, to: string, text: string) {
  const res = await fetch(`https://graph.facebook.com/${config.graphApiVersion}/${phoneNumberId}/messages`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ messaging_product: "whatsapp", to, type: "text", text: { body: text.slice(0, 4096) } }),
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`WhatsApp HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.json();
}

export async function verifyWhatsAppCredentials(phoneNumberId: string, accessToken: string) {
  const res = await fetch(`https://graph.facebook.com/${config.graphApiVersion}/${phoneNumberId}?fields=display_phone_number,verified_name`, {
    headers: { authorization: `Bearer ${accessToken}` }, signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`Credenciais WhatsApp inválidas (HTTP ${res.status})`);
  return res.json() as Promise<{ display_phone_number: string; verified_name: string }>;
}

import { config } from "../lib/config.js";

async function tg(token: string, method: string, body: unknown) {
  const res = await fetch(`${config.telegramApiBase}/bot${token}/${method}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(15000),
  });
  const data = await res.json() as { ok: boolean; result?: any; description?: string };
  if (!data.ok) throw new Error(`Telegram ${method}: ${data.description ?? res.status}`);
  return data.result;
}

export const telegram = {
  getMe: (token: string) => tg(token, "getMe", {}) as Promise<{ id: number; username: string }>,
  setWebhook: (token: string, url: string, secret: string) =>
    tg(token, "setWebhook", { url, secret_token: secret, allowed_updates: ["message"], drop_pending_updates: true }),
  deleteWebhook: (token: string) => tg(token, "deleteWebhook", {}),
  sendMessage: (token: string, chatId: string, text: string) => tg(token, "sendMessage", { chat_id: chatId, text: text.slice(0, 4096) }),
  sendChatAction: (token: string, chatId: string) => tg(token, "sendChatAction", { chat_id: chatId, action: "typing" }).catch(() => undefined),
};

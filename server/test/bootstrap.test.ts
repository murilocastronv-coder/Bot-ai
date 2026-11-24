import { describe, expect, it } from "vitest";
import { mockFetch } from "./helpers.js";
import { prisma } from "../src/lib/db.js";
import { runBootstrap } from "../src/services/bootstrap.js";

describe("bootstrap por variáveis de ambiente", () => {
  it("cria dono + negócio e conecta o Telegram uma única vez", async () => {
    Object.assign(process.env, { BOOTSTRAP_OWNER_EMAIL: "dono@boot.dev", BOOTSTRAP_OWNER_PASSWORD: "senha-muito-segura", BOOTSTRAP_BUSINESS_NAME: "Loja X", BOOTSTRAP_TEMPLATE: "barber", TELEGRAM_BOT_TOKEN: "123456789:AAEhBOweik6ad9r_QXMENQjcrGbqCr4K-ra" });
    let hookUrl = "";
    const calls = mockFetch({
      "/getMe": () => ({ ok: true, result: { id: 1, username: "loja_bot" } }),
      "/setWebhook": (_u, i) => { hookUrl = i.json.url; return { ok: true, result: true }; },
      "/getWebhookInfo": () => ({ ok: true, result: { url: hookUrl } }),
      "/setMyCommands": () => ({ ok: true, result: true }),
      "/deleteMyCommands": () => ({ ok: true, result: true }),
    });
    await runBootstrap();
    await runBootstrap();
    const u = await prisma.user.findUniqueOrThrow({ where: { email: "dono@boot.dev" }, include: { business: true } });
    expect(u.role).toBe("SUPERADMIN");
    expect(u.business).toMatchObject({ name: "Loja X", template: "barber", plan: "BUSINESS", telegramBotUsername: "loja_bot" });
    expect(calls.filter((c) => c.url.endsWith("/setWebhook"))).toHaveLength(1);
    const cmds = calls.filter((c) => c.url.endsWith("/setMyCommands"));
    expect(cmds).toHaveLength(2); // 1 por inicialização, só no idioma principal
    expect(cmds[0].body.language_code).toBeUndefined();
    expect(cmds[0].body.commands.find((c: any) => c.command === "servicos").description).toBe("Serviços e preços");
    for (const k of ["BOOTSTRAP_OWNER_EMAIL", "BOOTSTRAP_OWNER_PASSWORD", "BOOTSTRAP_BUSINESS_NAME", "BOOTSTRAP_TEMPLATE", "TELEGRAM_BOT_TOKEN"]) delete process.env[k];
  });
});
